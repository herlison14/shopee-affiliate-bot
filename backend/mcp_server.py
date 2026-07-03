from mcp.server.fastmcp import FastMCP, Context
from mcp.server.transport_security import TransportSecuritySettings
from sqlalchemy import select

import database
from models.agent_action import AgentAction
from models.campaign import Campaign
from models.commission import Commission
from models.user import User
from services import instagram_service
from services.ai_service import generate_caption_and_hashtags
from services.instagram_service import InstagramError
from services.shopee_url import (
    UNSTABLE_URL_WARNING,
    is_stable_product_url,
    normalize_product_url,
)

mcp = FastMCP(
    "ShopeeViral.AI",
    instructions=(
        "Ferramentas para gerenciar campanhas de afiliado Shopee e consultar comissoes. "
        "Cada usuario tem sua propria URL com token; as ferramentas atuam apenas sobre os "
        "dados do usuario dono do token presente na URL. O agente autonomo James roda em "
        "background e tambem toma acoes (promove rascunhos, renova legendas sem vendas, "
        "sugere replicar campanhas que venderam); use 'historico_agente' para ver o que "
        "ele ja fez e 'definir_agente_ativo' para liga-lo ou desliga-lo. Use "
        "'existe_campanha_para_produto' antes de criar uma campanha para evitar "
        "duplicar produto, e 'atualizar_status_campanha' apos tentar postar de "
        "verdade (nunca reporte 'posted' sem confirmar)."
    ),
    stateless_http=True,
    streamable_http_path="/mcp",
    # A URL ja contem um token de acesso secreto por usuario; a checagem de Host/Origin
    # do navegador nao se aplica a clientes MCP (Claude Desktop, ChatGPT, CLIs).
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)


class McpAuthError(Exception):
    pass


async def _get_user(ctx: Context) -> User:
    request = ctx.request_context.request
    token = request.path_params.get("token") if request else None
    if not token:
        raise McpAuthError("Token MCP ausente na URL.")

    async with database.AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.mcp_token == token))
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            raise McpAuthError("Token MCP invalido ou usuario inativo.")
        return user


@mcp.tool()
async def listar_campanhas(ctx: Context) -> list[dict]:
    """Lista as campanhas de afiliado Shopee do usuario, mais recentes primeiro."""
    user = await _get_user(ctx)
    async with database.AsyncSessionLocal() as db:
        result = await db.execute(
            select(Campaign).where(Campaign.user_id == user.id).order_by(Campaign.created_at.desc())
        )
        campaigns = result.scalars().all()
        return [
            {
                "id": c.id,
                "produto": c.product_name,
                "url_produto": c.product_url,
                "link_afiliado": c.affiliate_link,
                "legenda": c.caption,
                "hashtags": c.hashtags,
                "status": c.status,
                "criado_em": c.created_at.isoformat(),
            }
            for c in campaigns
        ]


@mcp.tool()
async def criar_campanha(
    ctx: Context,
    nome_produto: str,
    url_produto: str,
    link_afiliado: str | None = None,
) -> dict:
    """Cria uma nova campanha de afiliado Shopee para um produto, gerando legenda e
    hashtags virais automaticamente via IA."""
    user = await _get_user(ctx)
    caption, hashtags = await generate_caption_and_hashtags(nome_produto)

    # URL de oferta/temporaria expira: normaliza pra forma canonica e sinaliza
    # quando a URL nao fixa um produto estavel.
    product_url = normalize_product_url(url_produto)
    url_estavel = is_stable_product_url(product_url)

    async with database.AsyncSessionLocal() as db:
        campaign = Campaign(
            user_id=user.id,
            product_name=nome_produto,
            product_url=product_url,
            affiliate_link=link_afiliado,
            caption=caption,
            hashtags=hashtags,
            status="draft",
            status_detail=None if url_estavel else UNSTABLE_URL_WARNING,
        )
        db.add(campaign)
        await db.commit()
        await db.refresh(campaign)
        resultado = {
            "id": campaign.id,
            "produto": campaign.product_name,
            "url_produto": campaign.product_url,
            "legenda": campaign.caption,
            "hashtags": campaign.hashtags,
            "status": campaign.status,
        }
        if not url_estavel:
            resultado["aviso"] = UNSTABLE_URL_WARNING
        return resultado


@mcp.tool()
async def existe_campanha_para_produto(ctx: Context, url_produto: str) -> dict:
    """Verifica se ja existe uma campanha para essa URL de produto (use antes de criar
    uma campanha nova, para evitar duplicar/repostar o mesmo produto)."""
    user = await _get_user(ctx)
    async with database.AsyncSessionLocal() as db:
        result = await db.execute(
            select(Campaign).where(Campaign.user_id == user.id, Campaign.product_url == url_produto)
        )
        existentes = result.scalars().all()
        return {
            "existe": len(existentes) > 0,
            "campanhas": [{"id": c.id, "status": c.status} for c in existentes],
        }


VALID_STATUSES = {"draft", "scheduled", "posted", "failed", "needs_review"}


@mcp.tool()
async def atualizar_status_campanha(
    ctx: Context,
    campaign_id: str,
    status: str,
    detalhe: str | None = None,
    url_postagem: str | None = None,
) -> dict:
    """Atualiza o status de uma campanha apos uma tentativa de postagem.

    status deve ser um de: draft, scheduled, posted, failed, needs_review.
    So reporte 'posted' se a postagem foi de fato confirmada — caso contrario,
    use 'needs_review' com o 'detalhe' explicando o que aconteceu.
    """
    if status not in VALID_STATUSES:
        return {"erro": f"Status invalido. Use um de: {sorted(VALID_STATUSES)}"}

    user = await _get_user(ctx)
    async with database.AsyncSessionLocal() as db:
        result = await db.execute(
            select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == user.id)
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            return {"erro": "Campanha nao encontrada"}

        campaign.status = status
        campaign.status_detail = detalhe
        if url_postagem is not None:
            campaign.posted_url = url_postagem
        await db.commit()
        return {"id": campaign.id, "status": campaign.status}


@mcp.tool()
async def definir_link_afiliado(ctx: Context, campaign_id: str, link_afiliado: str) -> dict:
    """Define ou atualiza o link de afiliado de uma campanha existente. Use depois de
    gerar o link na Shopee, para a campanha aparecer na vitrine publica."""
    user = await _get_user(ctx)
    async with database.AsyncSessionLocal() as db:
        result = await db.execute(
            select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == user.id)
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            return {"erro": "Campanha nao encontrada"}
        campaign.affiliate_link = link_afiliado
        await db.commit()
        return {"id": campaign.id, "link_afiliado": campaign.affiliate_link}


@mcp.tool()
async def definir_url_produto(ctx: Context, campaign_id: str, url_produto: str) -> dict:
    """Troca a URL do produto de uma campanha existente (ex: consertar uma que nasceu
    com link de oferta temporario). A URL e normalizada pra forma canonica e o aviso
    de URL instavel e recalculado. Mantem legenda, hashtags e link de afiliado."""
    user = await _get_user(ctx)
    product_url = normalize_product_url(url_produto)
    url_estavel = is_stable_product_url(product_url)
    async with database.AsyncSessionLocal() as db:
        result = await db.execute(
            select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == user.id)
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            return {"erro": "Campanha nao encontrada"}
        campaign.product_url = product_url
        campaign.status_detail = None if url_estavel else UNSTABLE_URL_WARNING
        await db.commit()
        resultado = {"id": campaign.id, "url_produto": campaign.product_url}
        if not url_estavel:
            resultado["aviso"] = UNSTABLE_URL_WARNING
        return resultado


@mcp.tool()
async def postar_no_instagram(ctx: Context, campaign_id: str) -> dict:
    """Publica uma campanha no feed do Instagram (foto + legenda) via API oficial.
    Requer a conta do Instagram conectada e a campanha com image_url preenchida."""
    user = await _get_user(ctx)
    async with database.AsyncSessionLocal() as db:
        result = await db.execute(
            select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == user.id)
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            return {"erro": "Campanha nao encontrada"}
        if not user.instagram_access_token:
            return {"erro": "Conta Instagram nao conectada."}
        if not campaign.image_url:
            return {"erro": "Campanha sem imagem: adicione uma image_url para postar no Instagram."}

        caption = instagram_service.build_caption(campaign.caption, campaign.hashtags)
        try:
            pub = await instagram_service.publish_photo(user, campaign.image_url, caption)
        except InstagramError as exc:
            campaign.status = "needs_review"
            campaign.status_detail = f"Falha ao publicar no Instagram: {exc}"
            await db.commit()
            return {"erro": str(exc)}

        campaign.status = "posted"
        campaign.posted_url = pub["posted_url"]
        campaign.status_detail = None
        await db.commit()
        return {"id": campaign.id, "status": campaign.status, "posted_url": pub["posted_url"]}


@mcp.tool()
async def remover_campanha(ctx: Context, campaign_id: str) -> dict:
    """Remove uma campanha de afiliado pelo ID."""
    user = await _get_user(ctx)
    async with database.AsyncSessionLocal() as db:
        result = await db.execute(
            select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == user.id)
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            return {"erro": "Campanha nao encontrada"}
        await db.delete(campaign)
        await db.commit()
        return {"status": "removida", "id": campaign_id}


@mcp.tool()
async def resumo_comissoes(ctx: Context) -> dict:
    """Retorna o total de comissoes e o detalhe das vendas rastreadas do usuario."""
    user = await _get_user(ctx)
    async with database.AsyncSessionLocal() as db:
        result = await db.execute(
            select(Commission)
            .join(Campaign, Commission.campaign_id == Campaign.id)
            .where(Campaign.user_id == user.id)
            .order_by(Commission.created_at.desc())
        )
        commissions = result.scalars().all()
        total = sum(float(c.commission_amount) for c in commissions)
        return {
            "total_comissoes": round(total, 2),
            "quantidade_vendas": len(commissions),
            "vendas": [
                {
                    "pedido": c.order_id,
                    "valor_venda": float(c.sale_amount),
                    "comissao": float(c.commission_amount),
                    "status": c.status,
                }
                for c in commissions
            ],
        }


@mcp.tool()
async def historico_agente(ctx: Context) -> list[dict]:
    """Lista as acoes mais recentes que o agente autonomo James tomou sozinho
    (sem o usuario pedir), como promover rascunhos ou renovar legendas sem vendas."""
    user = await _get_user(ctx)
    async with database.AsyncSessionLocal() as db:
        result = await db.execute(
            select(AgentAction)
            .where(AgentAction.user_id == user.id)
            .order_by(AgentAction.created_at.desc())
            .limit(50)
        )
        actions = result.scalars().all()
        return [
            {
                "id": a.id,
                "campanha_id": a.campaign_id,
                "tipo": a.action_type,
                "descricao": a.description,
                "quando": a.created_at.isoformat(),
            }
            for a in actions
        ]


@mcp.tool()
async def definir_agente_ativo(ctx: Context, ativo: bool) -> dict:
    """Liga ou desliga o agente autonomo James para o usuario. Quando desligado,
    James para de promover rascunhos, renovar legendas e sugerir replicacoes."""
    user = await _get_user(ctx)
    async with database.AsyncSessionLocal() as db:
        db_user = await db.get(User, user.id)
        db_user.agent_enabled = ativo
        await db.commit()
        return {"agente_ativo": db_user.agent_enabled}
