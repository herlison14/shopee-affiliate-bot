"""
Shopee Affiliate Platform browser automation using Playwright.

First-run setup:
  Set HEADLESS=false in .env, run pipeline once, complete OTP manually.
  Session is saved to data/.shopee_session.json for all subsequent runs.
"""

import asyncio
import json
import logging
import os
import random
from pathlib import Path

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from converter.link_converter import build_subids, inject_subids_into_url

logger = logging.getLogger(__name__)

# ── DOM Selectors (update here if Shopee changes their frontend) ────────────
SELECTORS = {
    # Login page (shopee.com.br/buyer/login)
    "login_email": "input[name='loginKey'], input[type='text'], input[type='email']",
    "login_password": "input[name='password'], input[type='password']",
    "login_submit": "button[type='submit']",
    "otp_input": "input[placeholder*='OTP'], input[placeholder*='código'], input[placeholder*='verificação']",
    "dashboard_indicator": ".sidebar-menu, nav, [class*='affiliate'], [class*='dashboard'], .shopee-header",

    # Product discovery (affiliate.shopee.com.br/offer/product_offer)
    "product_list_item": ".product-item, [class*='product-item'], [class*='offer-item']",
    "product_name": ".product-name, [class*='product-name'], [class*='item-name']",
    "product_link": "a[href*='shopee.com.br/']",
    "commission_badge": ".commission-rate, [class*='commission-rate'], [class*='Taxa de comissão']",
    "get_link_btn": "button:has-text('Obter link'), button:has-text('Obter Link')",
    "pagination_next": "button[aria-label*='next'], .next-page, li.ant-pagination-next button",

    # Link personalizado (affiliate.shopee.com.br/offer/custom_link)
    "custom_link_menu": "a[href*='custom_link'], .sidebar-menu a:has-text('Link personalizado')",
    "link_input": "textarea",
    "subid1_input": "input[placeholder*='Calçados Esportivos']",
    "subid2_input": "input[placeholder*='InstagramFeed']",
    "subid3_input": "input[placeholder*='BirthdaySale']",
    "generate_btn": "button:has-text('Obter link')",
    "copy_link_result": "input[readonly], [class*='result'], [class*='link-result']",

    # Campanhas (affiliate.shopee.com.br/campaign/campaign_list)
    "campaign_list_url": "campaign/campaign_list",

    # Commission details
    "view_details_btn": "button:has-text('Ver Detalhes'), button:has-text('Ver Mais')",
    "commission_new": "[class*='new-buyer'], [class*='newBuyer'], [class*='novo']",
    "commission_existing": "[class*='existing-buyer'], [class*='existingBuyer'], [class*='atual']",
}

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


class OTPRequiredException(Exception):
    pass


async def _delay(min_s: float = 0.5, max_s: float = 2.5):
    """Human-like random delay."""
    await asyncio.sleep(random.uniform(min_s, max_s))


async def _screenshot(page: Page, name: str, screenshots_dir: str):
    """Save a debug screenshot."""
    Path(screenshots_dir).mkdir(parents=True, exist_ok=True)
    path = os.path.join(screenshots_dir, f"{name}.png")
    await page.screenshot(path=path)
    logger.debug(f"Screenshot salvo: {path}")


async def launch_browser(headless: bool = True):
    """Launch Playwright Chromium with anti-detection settings."""
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=headless)
    context = await browser.new_context(user_agent=USER_AGENT)
    await context.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    page = await context.new_page()
    return playwright, browser, context, page


async def login(
    page: Page,
    context: BrowserContext,
    email: str,
    password: str,
    affiliate_url: str,
    session_path: str,
    screenshots_dir: str,
    headless: bool,
) -> bool:
    """
    Login to the Shopee Affiliate portal.
    Loads saved session first; re-authenticates if session is expired.
    """
    # Try loading saved session
    if os.path.exists(session_path):
        logger.info("Carregando sessão salva...")
        await context.add_cookies(
            json.loads(Path(session_path).read_text()).get("cookies", [])
        )
        await page.goto(affiliate_url, wait_until="networkidle", timeout=30000)
        await _delay()
        if await _is_logged_in(page):
            logger.info("Sessão restaurada com sucesso.")
            return True
        logger.warning("Sessão expirada, fazendo login novamente...")

    # Fresh login — navega para o portal que redireciona para shopee.com.br/buyer/login
    await page.goto(affiliate_url, wait_until="networkidle", timeout=30000)
    await _delay(2, 4)
    # Se redirecionou para login da Shopee, aguarda a página carregar
    if "buyer/login" in page.url or "login" in page.url:
        logger.info("Redirecionado para página de login da Shopee...")

    for attempt in range(3):
        try:
            await page.fill(SELECTORS["login_email"], email)
            await _delay(0.3, 0.8)
            await page.fill(SELECTORS["login_password"], password)
            await _delay(0.3, 0.8)
            await page.click(SELECTORS["login_submit"])
            await _delay(2, 4)

            # Check for OTP
            otp_visible = await page.is_visible(SELECTORS["otp_input"])
            if otp_visible:
                if headless:
                    logger.error(
                        "OTP requerido! Execute com HEADLESS=false para inserir o código manualmente."
                    )
                    raise OTPRequiredException(
                        "Configure HEADLESS=false no .env para o primeiro login com OTP."
                    )
                logger.info("OTP detectado. Aguardando inserção manual no navegador...")
                # Wait up to 60s for manual OTP entry
                await page.wait_for_selector(
                    SELECTORS["dashboard_indicator"], timeout=60000
                )

            if await _is_logged_in(page):
                # Save session
                storage = await context.storage_state()
                Path(session_path).parent.mkdir(parents=True, exist_ok=True)
                Path(session_path).write_text(json.dumps(storage))
                logger.info("Login realizado e sessão salva.")
                return True

        except OTPRequiredException:
            raise
        except Exception as e:
            logger.warning(f"Tentativa de login {attempt + 1} falhou: {e}")
            await _screenshot(page, f"login_error_{attempt}", screenshots_dir)
            await _delay(2, 5)

    logger.error("Login falhou após 3 tentativas.")
    return False


async def _is_logged_in(page: Page) -> bool:
    """Check if the current page shows an authenticated state."""
    try:
        return await page.is_visible(SELECTORS["dashboard_indicator"], timeout=5000)
    except Exception:
        return False


async def discover_products(
    page: Page,
    max_products: int = 100,
    min_commission_pct: float = 5.0,
    affiliate_url: str = "https://affiliate.shopee.com.br",
    screenshots_dir: str = "logs/screenshots",
) -> list:
    """
    Navigate the affiliate product discovery section and collect raw product data.
    """
    products = []
    logger.info(f"Descobrindo produtos (máx: {max_products}, comissão mín: {min_commission_pct}%)...")

    try:
        await page.goto(
            f"{affiliate_url}/offer/product_offer",
            wait_until="networkidle",
            timeout=30000,
        )
        await _delay(2, 4)

        page_num = 1
        while len(products) < max_products:
            logger.info(f"Página {page_num} — produtos coletados: {len(products)}")

            # Wait for product items to load
            try:
                await page.wait_for_selector(
                    SELECTORS["product_list_item"], timeout=15000
                )
            except Exception:
                logger.warning("Nenhum produto encontrado nesta página.")
                break

            items = await page.query_selector_all(SELECTORS["product_list_item"])
            for item in items:
                if len(products) >= max_products:
                    break
                try:
                    product = await _extract_product_from_element(item, min_commission_pct)
                    if product:
                        products.append(product)
                except Exception as e:
                    logger.debug(f"Erro ao extrair produto: {e}")
                    continue

            # Try pagination
            next_btn = await page.query_selector(SELECTORS["pagination_next"])
            if not next_btn:
                break
            is_disabled = await next_btn.get_attribute("disabled")
            if is_disabled:
                break

            await next_btn.click()
            await _delay(2, 4)
            page_num += 1

    except Exception as e:
        logger.error(f"Erro ao descobrir produtos: {e}")
        await _screenshot(page, "discover_error", screenshots_dir)

    logger.info(f"Total de produtos descobertos: {len(products)}")
    return products


async def _extract_product_from_element(element, min_commission_pct: float) -> dict | None:
    """Extract product data from a DOM element."""
    try:
        name_el = await element.query_selector(SELECTORS["product_name"])
        name = (await name_el.inner_text()).strip() if name_el else ""

        link_el = await element.query_selector(SELECTORS["product_link"])
        original_url = await link_el.get_attribute("href") if link_el else ""

        commission_el = await element.query_selector(SELECTORS["commission_badge"])
        commission_text = (await commission_el.inner_text()).strip() if commission_el else "0%"

        # Parse commission percentage
        commission_pct = _parse_commission(commission_text)
        if commission_pct < min_commission_pct:
            return None

        if not name or not original_url:
            return None

        # Extract product ID from URL
        product_id = _extract_product_id(original_url)

        return {
            "produto": name,
            "product_id": product_id,
            "link_original": original_url,
            "comissao_novo": commission_pct,
            "comissao_atual": commission_pct * 0.5,  # fallback; updated in get_affiliate_link
            "thumbnail_url": "",
            "category": "",
        }
    except Exception:
        return None


def _parse_commission(text: str) -> float:
    """Extract numeric commission value from strings like '12.5%' or '12,5%'."""
    cleaned = text.replace("%", "").replace(",", ".").strip()
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _extract_product_id(url: str) -> str:
    """Extract the product ID from a Shopee product URL."""
    import re
    match = re.search(r"i\.(\d+)\.(\d+)", url)
    if match:
        return f"{match.group(1)}.{match.group(2)}"
    match = re.search(r"-i\.(\d+)", url)
    if match:
        return match.group(1)
    return url.rstrip("/").split("-")[-1] if url else ""


async def get_affiliate_link(
    page: Page,
    product: dict,
    subids: dict,
    affiliate_url: str = "https://affiliate.shopee.com.br",
    screenshots_dir: str = "logs/screenshots",
) -> str | None:
    """
    Use the affiliate portal's Custom Link tool to generate a tracked affiliate link.
    Fills SubID fields with tracking data.
    """
    try:
        await page.goto(
            f"{affiliate_url}/offer/custom_link",
            wait_until="networkidle",
            timeout=30000,
        )
        await _delay(1, 2)

        # Fill product URL
        await page.fill(SELECTORS["link_input"], product["link_original"])
        await _delay(0.5, 1)

        # Fill SubID fields
        subid_values = [
            subids.get("nome_do_produto", ""),
            subids.get("rede_social", ""),
            subids.get("campanha_atual", ""),
        ]
        for selector, value in zip(
            [SELECTORS["subid1_input"], SELECTORS["subid2_input"], SELECTORS["subid3_input"]],
            subid_values,
        ):
            try:
                if await page.is_visible(selector, timeout=3000):
                    await page.fill(selector, value)
                    await _delay(0.2, 0.5)
            except Exception:
                pass

        # Click generate
        await page.click(SELECTORS["generate_btn"])
        await _delay(2, 3)

        # Capture result link
        result_el = await page.query_selector(SELECTORS["copy_link_result"])
        if result_el:
            link = await result_el.get_attribute("value") or await result_el.inner_text()
            link = link.strip()
            if link:
                logger.debug(f"Link afiliado gerado: {link[:60]}...")
                return link

        logger.warning(f"Link afiliado não capturado para: {product['produto']}")
        await _screenshot(page, f"link_gen_error_{product['product_id']}", screenshots_dir)
        return None

    except Exception as e:
        logger.error(f"Erro ao gerar link para {product['produto']}: {e}")
        await _screenshot(page, f"link_gen_exception_{product['product_id']}", screenshots_dir)
        return None


async def scrape_all_products(settings) -> list:
    """
    Full scraping orchestrator:
    login → discover products → generate affiliate links for each.
    Returns enriched list of product dicts.
    """
    playwright, browser, context, page = await launch_browser(headless=settings.headless)

    try:
        logged_in = await login(
            page=page,
            context=context,
            email=settings.shopee_email,
            password=settings.shopee_password,
            affiliate_url=settings.shopee_affiliate_url,
            session_path=settings.SESSION_PATH,
            screenshots_dir=settings.SCREENSHOTS_DIR,
            headless=settings.headless,
        )

        if not logged_in:
            logger.error("Não foi possível fazer login. Abortando scraping.")
            return []

        raw_products = await discover_products(
            page=page,
            max_products=settings.max_products,
            min_commission_pct=settings.min_commission_pct,
            affiliate_url=settings.shopee_affiliate_url,
            screenshots_dir=settings.SCREENSHOTS_DIR,
        )

        enriched = []
        for i, product in enumerate(raw_products):
            logger.info(f"[{i+1}/{len(raw_products)}] Gerando link: {product['produto'][:50]}")

            subids = build_subids(
                product_name=product["produto"],
                social_network=settings.social_network,
                campaign=settings.campaign_name,
            )

            affiliate_link = await get_affiliate_link(
                page=page,
                product=product,
                subids=subids,
                affiliate_url=settings.shopee_affiliate_url,
                screenshots_dir=settings.SCREENSHOTS_DIR,
            )

            product["link_afiliado"] = affiliate_link or product["link_original"]
            product["subids"] = subids
            enriched.append(product)
            await _delay(1, 2)

        return enriched

    finally:
        await browser.close()
        await playwright.stop()
