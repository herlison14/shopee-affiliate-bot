"""
Seller Follower — Segue automaticamente os vendedores Shopee cujos
produtos foram capturados durante o scraping.

Fluxo:
  1. Extrai shop_id da URL do produto (formato: .../produto-i.SHOP_ID.ITEM_ID)
  2. Navega para shopee.com.br/shop/{shop_id}
  3. Clica no botão "Seguir" se ainda não estiver seguindo
  4. Registra resultado em data/followed_sellers.json

Uso:
  from scraper.seller_follower import follow_sellers_from_products
  await follow_sellers_from_products(page, products)
"""

import asyncio
import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

FOLLOWED_DB_PATH = Path("data/followed_sellers.json")

# Seletores do botão Seguir na página do vendedor Shopee
FOLLOW_SELECTORS = [
    "button:has-text('Seguir')",
    "button:has-text('Follow')",
    "[class*='follow-btn']:not([class*='following'])",
    "button[class*='follow']:not([class*='unfollow'])",
    ".shopee-button-outline:has-text('Seguir')",
]

# Seletores que indicam que já está seguindo
ALREADY_FOLLOWING_SELECTORS = [
    "button:has-text('Seguindo')",
    "button:has-text('Following')",
    "[class*='following-btn']",
    "button[class*='unfollow']",
]


# ── Persistência ───────────────────────────────────────────────────────────────

def _load_followed() -> dict:
    """Carrega lista de vendedores já seguidos."""
    FOLLOWED_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if FOLLOWED_DB_PATH.exists():
        try:
            return json.loads(FOLLOWED_DB_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_followed(data: dict):
    """Salva lista de vendedores seguidos."""
    FOLLOWED_DB_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


# ── Extração de shop_id ────────────────────────────────────────────────────────

def extract_shop_id(url: str) -> str | None:
    """
    Extrai o shop_id de uma URL de produto Shopee.

    Formatos suportados:
      - shopee.com.br/produto-i.{SHOP_ID}.{ITEM_ID}
      - shopee.com.br/shop/{SHOP_ID}
      - affiliate.shopee.com.br/...?item={ITEM_ID}&shop={SHOP_ID}
    """
    if not url:
        return None

    # Formato padrão: -i.SHOP_ID.ITEM_ID
    match = re.search(r"-i\.(\d+)\.(\d+)", url)
    if match:
        return match.group(1)

    # Formato /shop/ID
    match = re.search(r"/shop/(\d+)", url)
    if match:
        return match.group(1)

    # Query param shop=ID
    match = re.search(r"[?&]shop[_id]*=(\d+)", url)
    if match:
        return match.group(1)

    return None


def extract_seller_name(url: str) -> str | None:
    """Extrai o nome do vendedor da URL (shopee.com.br/{seller_name}/...)."""
    match = re.search(r"shopee\.com\.br/([^/?#]+)/", url)
    if match:
        name = match.group(1)
        # Ignora paths comuns que não são nomes de vendedor
        if name not in ("shop", "product", "buyer", "search", "m"):
            return name
    return None


# ── Follow ─────────────────────────────────────────────────────────────────────

async def follow_seller(page, shop_id: str, seller_name: str = "") -> str:
    """
    Segue um vendedor no Shopee.

    Returns:
        "seguido"       — seguiu agora
        "ja_seguindo"   — já estava seguindo
        "nao_logado"    — página pediu login
        "falhou"        — erro ou botão não encontrado
    """
    followed_db = _load_followed()

    # Já seguido anteriormente?
    if shop_id in followed_db:
        logger.debug(f"Vendedor {shop_id} já foi seguido anteriormente.")
        return "ja_seguindo"

    shop_url = f"https://shopee.com.br/shop/{shop_id}"
    display = seller_name or shop_id

    try:
        logger.info(f"Visitando loja: {display} ({shop_url})")
        await page.goto(shop_url, wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(2)

        # Verifica se foi redirecionado para login
        if "login" in page.url or "buyer/login" in page.url:
            logger.warning(f"Shopee pediu login para seguir {display}")
            return "nao_logado"

        # Verifica se já está seguindo
        for sel in ALREADY_FOLLOWING_SELECTORS:
            try:
                el = await page.query_selector(sel)
                if el:
                    logger.info(f"Já seguindo: {display}")
                    followed_db[shop_id] = {
                        "nome": seller_name,
                        "url": shop_url,
                        "status": "ja_seguindo",
                    }
                    _save_followed(followed_db)
                    return "ja_seguindo"
            except Exception:
                pass

        # Tenta clicar em Seguir
        clicked = False
        for sel in FOLLOW_SELECTORS:
            try:
                btn = await page.query_selector(sel)
                if btn:
                    await btn.scroll_into_view_if_needed()
                    await asyncio.sleep(0.5)
                    await btn.click()
                    await asyncio.sleep(1.5)
                    clicked = True
                    logger.info(f"✅ Seguindo agora: {display}")
                    break
            except Exception:
                continue

        if not clicked:
            # Tenta via JavaScript como fallback
            clicked = await page.evaluate("""
                () => {
                    const btns = Array.from(document.querySelectorAll('button'))
                        .filter(b => /^seguir$|^follow$/i.test(b.textContent.trim()));
                    if (btns.length > 0) { btns[0].click(); return true; }
                    return false;
                }
            """)
            if clicked:
                await asyncio.sleep(1.5)
                logger.info(f"✅ Seguindo agora (JS): {display}")

        if clicked:
            followed_db[shop_id] = {
                "nome": seller_name,
                "url": shop_url,
                "status": "seguido",
            }
            _save_followed(followed_db)
            return "seguido"
        else:
            logger.warning(f"Botão Seguir não encontrado para: {display}")
            return "falhou"

    except Exception as e:
        logger.error(f"Erro ao seguir vendedor {display}: {e}")
        return "falhou"


# ── Follow em lote (chamado após scraping) ────────────────────────────────────

async def follow_sellers_from_products(
    page,
    products: list,
    max_follows: int = 50,
    delay_between: float = 2.0,
) -> dict:
    """
    Segue automaticamente os vendedores de uma lista de produtos.

    Args:
        page: Playwright page já autenticada no Shopee
        products: lista de dicts com 'link_original' ou 'link_afiliado'
        max_follows: limite de follows por execução (evita rate limit)
        delay_between: segundos entre cada follow

    Returns:
        dict com contagens: {'seguido': N, 'ja_seguindo': N, 'falhou': N}
    """
    stats = {"seguido": 0, "ja_seguindo": 0, "falhou": 0, "nao_logado": 0}
    seen_shops = set()
    count = 0

    logger.info(f"Iniciando auto-follow de vendedores ({len(products)} produtos, máx {max_follows} follows)")

    for product in products:
        if count >= max_follows:
            logger.info(f"Limite de {max_follows} follows atingido.")
            break

        # Pega a URL mais rica (link original tem shop_id, afiliado pode não ter)
        url = product.get("link_original", "") or product.get("link_afiliado", "")
        shop_id = extract_shop_id(url)

        if not shop_id or shop_id in seen_shops:
            continue

        seen_shops.add(shop_id)
        seller_name = extract_seller_name(url) or product.get("produto", "")[:30]

        result = await follow_seller(page, shop_id, seller_name)
        stats[result] = stats.get(result, 0) + 1

        if result == "nao_logado":
            logger.error("Sessão Shopee expirou. Interrompendo follows.")
            break

        if result == "seguido":
            count += 1
            await asyncio.sleep(delay_between)
        else:
            await asyncio.sleep(0.5)

    logger.info(
        f"Auto-follow concluído: {stats['seguido']} seguidos | "
        f"{stats['ja_seguindo']} já seguindo | {stats['falhou']} falhou"
    )
    return stats


# ── Relatório de vendedores seguidos ──────────────────────────────────────────

def get_followed_report() -> dict:
    """Retorna relatório dos vendedores seguidos."""
    data = _load_followed()
    seguidos = [v for v in data.values() if v.get("status") == "seguido"]
    ja_seguindo = [v for v in data.values() if v.get("status") == "ja_seguindo"]

    return {
        "total": len(data),
        "seguidos_pelo_bot": len(seguidos),
        "ja_seguia_antes": len(ja_seguindo),
        "vendedores": list(data.values()),
    }
