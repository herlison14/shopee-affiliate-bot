from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.campaign import Campaign
from models.user import User
from schemas import (
    VALID_CAMPAIGN_STATUSES,
    CampaignBulkCreate,
    CampaignBulkResult,
    CampaignCreate,
    CampaignEdit,
    CampaignOut,
    CampaignStatusUpdate,
)
from security import get_current_user
from services.ai_service import generate_caption_and_hashtags
from services.shopee_url import (
    UNSTABLE_URL_WARNING,
    is_stable_product_url,
    normalize_product_url,
)

router = APIRouter(prefix="/api/v1/campaigns", tags=["campaigns"])


@router.get("", response_model=list[CampaignOut])
async def list_campaigns(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    product_url: str | None = None,
):
    """Lista campanhas do usuario. Filtre por product_url para checar duplicidade
    antes de criar uma campanha nova para o mesmo produto."""
    query = select(Campaign).where(Campaign.user_id == current_user.id)
    if product_url:
        query = query.where(Campaign.product_url == product_url)
    result = await db.execute(query.order_by(Campaign.created_at.desc()))
    return result.scalars().all()


@router.post("", response_model=CampaignOut, status_code=201)
async def create_campaign(
    payload: CampaignCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    caption, hashtags = await generate_caption_and_hashtags(payload.product_name)

    scheduled_for = payload.scheduled_for
    if scheduled_for is not None and scheduled_for.tzinfo is not None:
        scheduled_for = scheduled_for.astimezone(timezone.utc).replace(tzinfo=None)

    # URL de oferta/temporaria expira: normaliza pra forma canonica quando da e
    # sinaliza (status_detail) quando a URL nao fixa um produto estavel.
    product_url = normalize_product_url(payload.product_url)
    status_detail = None if is_stable_product_url(product_url) else UNSTABLE_URL_WARNING

    campaign = Campaign(
        user_id=current_user.id,
        product_name=payload.product_name,
        product_url=product_url,
        affiliate_link=payload.affiliate_link,
        caption=caption,
        hashtags=hashtags,
        status="scheduled" if scheduled_for else "draft",
        scheduled_for=scheduled_for,
        status_detail=status_detail,
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.post("/bulk", response_model=CampaignBulkResult, status_code=201)
async def create_campaigns_bulk(
    payload: CampaignBulkCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cria varias campanhas de uma vez (ex: importadas de uma planilha). Gera legenda/
    hashtags via IA para cada uma. Pula produtos cuja product_url ja tem campanha
    (dedup), para reimportar a mesma planilha nao duplicar."""
    existentes = await db.execute(
        select(Campaign.product_url).where(Campaign.user_id == current_user.id)
    )
    urls_existentes = {row[0] for row in existentes.all()}

    criadas = []
    ignoradas = 0
    urls_neste_lote = set()
    for item in payload.items:
        # Normaliza antes do dedup: URLs diferentes do mesmo produto (slug vs
        # /product/...) viram a mesma forma canonica e sao deduplicadas juntas.
        product_url = normalize_product_url(item.product_url)
        if product_url in urls_existentes or product_url in urls_neste_lote:
            ignoradas += 1
            continue
        urls_neste_lote.add(product_url)

        caption, hashtags = await generate_caption_and_hashtags(item.product_name)
        campaign = Campaign(
            user_id=current_user.id,
            product_name=item.product_name,
            product_url=product_url,
            affiliate_link=item.affiliate_link,
            caption=caption,
            hashtags=hashtags,
            status="draft",
            status_detail=None if is_stable_product_url(product_url) else UNSTABLE_URL_WARNING,
        )
        db.add(campaign)
        criadas.append(campaign)

    await db.commit()
    for c in criadas:
        await db.refresh(c)

    return CampaignBulkResult(criadas=len(criadas), ignoradas_duplicadas=ignoradas, campaigns=criadas)


@router.get("/{campaign_id}", response_model=CampaignOut)
async def get_campaign(
    campaign_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == current_user.id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")
    return campaign


@router.patch("/{campaign_id}", response_model=CampaignOut)
async def edit_campaign(
    campaign_id: str,
    payload: CampaignEdit,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Edita campos de uma campanha existente (link de afiliado, legenda, hashtags).
    PATCH parcial: so altera os campos que vierem no corpo da requisicao."""
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == current_user.id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")

    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(campaign, field, value)

    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.patch("/{campaign_id}/status", response_model=CampaignOut)
async def update_campaign_status(
    campaign_id: str,
    payload: CampaignStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Atualiza o status de uma campanha (usado pelo orquestrador local apos tentar postar).

    Nao existe 'sucesso assumido': quem chama este endpoint deve ter confirmado de fato
    o resultado antes de reportar 'posted' — caso contrario, reportar 'needs_review'.
    """
    if payload.status not in VALID_CAMPAIGN_STATUSES:
        raise HTTPException(
            status_code=422, detail=f"Status invalido. Use um de: {sorted(VALID_CAMPAIGN_STATUSES)}"
        )

    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == current_user.id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")

    campaign.status = payload.status
    campaign.status_detail = payload.status_detail
    if payload.posted_url is not None:
        campaign.posted_url = payload.posted_url
    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.delete("/{campaign_id}", status_code=204)
async def delete_campaign(
    campaign_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == current_user.id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")
    await db.delete(campaign)
    await db.commit()
