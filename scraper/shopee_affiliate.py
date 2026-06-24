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
    """Save a debug screenshot (silently ignores errors if page is closed)."""
    try:
        Path(screenshots_dir).mkdir(parents=True, exist_ok=True)
        path = os.path.join(screenshots_dir, f"{name}.png")
        await page.screenshot(path=path)
        logger.debug(f"Screenshot salvo: {path}")
    except Exception as e:
        logger.debug(f"Screenshot ignorado ({name}): {e}")


_cdp_mode = False  # Flag global: True quando conectado via CDP (não fechar o browser ao terminar)


async def launch_browser(headless: bool = True):
    """Conecta ao Chrome existente via CDP ou lança novo com anti-detection."""
    global _cdp_mode
    playwright = await async_playwright().start()
    try:
        # Tenta conectar ao Chrome existente com remote debugging na porta 9222
        browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
        logger.info("Conectado ao Chrome existente via CDP!")
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        # Encontra a aba já aberta no affiliate.shopee.com.br ou abre nova
        page = None
        for p in context.pages:
            if "affiliate.shopee.com.br" in p.url:
                page = p
                logger.info(f"Usando aba existente: {p.url}")
                break
        if not page:
            page = context.pages[0] if context.pages else await context.new_page()
        _cdp_mode = True
        return playwright, browser, context, page
    except Exception:
        logger.info("Chrome CDP não disponível, iniciando novo navegador...")
        _cdp_mode = False

    try:
        browser = await playwright.chromium.launch(
            channel="chrome",
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars",
                "--start-maximized",
            ]
        )
    except Exception:
        browser = await playwright.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )

    context = await browser.new_context(
        user_agent=USER_AGENT,
        viewport={"width": 1366, "height": 768},
        locale="pt-BR",
        timezone_id="America/Sao_Paulo",
    )
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
        window.chrome = { runtime: {} };
    """)
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

    # Modo manual: aguarda o usuário fazer login completo no navegador (incluindo CAPTCHA)
    if not headless:
        logger.info("=" * 60)
        logger.info("AÇÃO NECESSÁRIA: Faça login manualmente no navegador!")
        logger.info("1. Preencha email e senha")
        logger.info("2. Resolva o CAPTCHA se aparecer")
        logger.info("3. Complete o OTP/SMS se pedir")
        logger.info("Aguardando até 3 minutos...")
        logger.info("=" * 60)
        try:
            # Aguarda até 10 minutos para o usuário completar login + CAPTCHA + OTP
            await page.wait_for_url(
                "**/affiliate.shopee.com.br/**",
                timeout=600000
            )
            await _delay(2, 3)
            if await _is_logged_in(page):
                storage = await context.storage_state()
                Path(session_path).parent.mkdir(parents=True, exist_ok=True)
                Path(session_path).write_text(json.dumps(storage))
                logger.info("Login realizado e sessão salva!")
                return True
        except Exception as e:
            logger.error(f"Tempo esgotado esperando login manual: {e}")
            return False

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
                await page.wait_for_selector(
                    SELECTORS["dashboard_indicator"], timeout=120000
                )

            if await _is_logged_in(page):
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
    """Check if the current page shows an authenticated state.

    Also considers the URL: if we are already on affiliate.shopee.com.br and
    there is no 'login' or '404' segment in the URL, the session is active.
    """
    try:
        current_url = page.url
        if (
            "affiliate.shopee.com.br" in current_url
            and "login" not in current_url
            and "404" not in current_url
        ):
            return True
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
    seen_urls = set()
    logger.info(f"Descobrindo produtos (máx: {max_products}, comissão mín: {min_commission_pct}%)...")

    # Seções de oferta para scraping — combinadas para atingir max_products
    offer_sections = [
        f"{affiliate_url}/offer/product_offer",
        f"{affiliate_url}/offer/shopee_offer",
        f"{affiliate_url}/offer/offer_for_me",
    ]

    for section_url in offer_sections:
        if len(products) >= max_products:
            break
        logger.info(f"Seção: {section_url.split('/')[-1]} ({len(products)}/{max_products} produtos coletados)")
        await _scrape_section(page, section_url, products, seen_urls, max_products, min_commission_pct, screenshots_dir)

    logger.info(f"Total de produtos descobertos: {len(products)}")
    return products


async def _scrape_section(page, target_url, products, seen_urls, max_products, min_commission_pct, screenshots_dir):
    """Extrai produtos de uma seção de oferta, com scroll infinito."""

    try:
        # Navega apenas se não estiver já na página correta
        if target_url not in page.url:
            await page.goto(target_url, wait_until="networkidle", timeout=30000)

        # Aguarda React renderizar os produtos (espera algum botão aparecer)
        logger.info("Aguardando React renderizar produtos...")
        await _delay(5, 7)

        # Scroll para triggerar lazy-loading
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 3)")
        await _delay(2, 3)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight * 2 / 3)")
        await _delay(2, 3)
        await page.evaluate("window.scrollTo(0, 0)")
        await _delay(2, 3)

        # ── Detecção de CAPTCHA — volta ao portal se redirecionado ───────────
        if "verify/captcha" in page.url or "verify/traffic" in page.url:
            logger.warning(f"CAPTCHA detectado! URL: {page.url[:120]}")
            logger.warning("Aguardando 30s e tentando novamente...")
            await _delay(28, 32)
            await page.goto(target_url, wait_until="networkidle", timeout=30000)
            await _delay(5, 8)
            if "verify/captcha" in page.url or "verify/traffic" in page.url:
                logger.error("CAPTCHA persiste. Resolva manualmente no Chrome e execute novamente.")
                return []

        # Screenshot de debug antes da extração
        await _screenshot(page, "before_extract", screenshots_dir)
        logger.info(f"URL atual: {page.url}")

        page_num = 1
        while len(products) < max_products:
            logger.info(f"Página {page_num} — produtos coletados: {len(products)}")

            # Aguarda mais um pouco para garantir renderização
            await _delay(2, 3)

            # ── Estratégia 1: JS robusto com múltiplas abordagens ──────────────
            js_products = await page.evaluate("""
                () => {
                    const results = [];
                    const seen = new Set();

                    // Palavras que indicam elemento de UI, não produto real
                    const UI_BLACKLIST = /^(português|english|español|中文|tiếng việt|bahasa|idioma|language|filtro|filter|categoria|category|ordenar|sort|buscar|search|login|entrar|cadastrar|menu|home|início|voltar|back|próximo|anterior|next|prev|page|página|loading|carregando|erro|error)$/i;

                    // URL de produto: formato antigo (shopee.com.br/...-i.ID) ou novo (affiliate.shopee.com.br/offer/product_offer/ID)
                    function isProductUrl(url) {
                        return /shopee\\.com\\.br\\/.*-i\\.\\d+\\.\\d+/.test(url) ||
                               /shopee\\.com\\.br\\/[^\\/]+\\/[^\\/]+-i\\.\\d+/.test(url) ||
                               /affiliate\\.shopee\\.com\\.br\\/offer\\/product_offer\\/\\d+/.test(url);
                    }

                    // Helper: encontra o ancestral mais próximo que contém comissão E link de produto
                    function findCard(startEl, maxLevels) {
                        let el = startEl;
                        for (let i = 0; i < maxLevels; i++) {
                            el = el.parentElement;
                            if (!el) return null;
                            const txt = el.innerText || '';
                            const hasComm = /\\d+[,.]?\\d*\\s*%/.test(txt);
                            const productLink = Array.from(el.querySelectorAll('a'))
                                .find(a => isProductUrl(a.href));
                            if (hasComm && productLink && txt.length > 40) return el;
                        }
                        return null;
                    }

                    // Extrai nome limpo: ignora linhas de UI, comissão, preço
                    function extractName(fullText, imgAlt) {
                        if (imgAlt && imgAlt.length > 10 && !UI_BLACKLIST.test(imgAlt.trim())) {
                            return imgAlt.trim().substring(0, 150);
                        }
                        const lines = fullText.split('\\n')
                            .map(t => t.trim())
                            .filter(t =>
                                t.length > 10 &&
                                !/^\\d+[,.]?\\d*\\s*%/.test(t) &&
                                !/^R\\$/.test(t) &&
                                !UI_BLACKLIST.test(t) &&
                                !/^\\d+$/.test(t)
                            );
                        return lines.length > 0 ? lines[0].substring(0, 150) : '';
                    }

                    // ── Estratégia A: via botões "Obter link" ─────────────────
                    const btns = Array.from(document.querySelectorAll('button'))
                        .filter(el => /obter\\s*link/i.test(el.textContent));

                    btns.forEach(btn => {
                        try {
                            const card = findCard(btn, 12);
                            if (!card) return;

                            const fullText = card.innerText || '';
                            const productLinks = Array.from(card.querySelectorAll('a'))
                                .filter(a => isProductUrl(a.href));
                            const href = productLinks.length > 0 ? productLinks[0].href : '';
                            if (!href || seen.has(href)) return;

                            const commMatches = fullText.match(/(\\d+(?:[,.]\\d+)?)\\s*%/g) || [];
                            const commValues = commMatches.map(m => parseFloat(m.replace('%','').replace(',','.')))
                                .filter(v => v > 0 && v <= 80);
                            const commission = commValues.length > 0 ? Math.max(...commValues) : 0;

                            const priceMatches = fullText.match(/R\$\s?[\d.,]+/g) || [];
                            const price = priceMatches.length > 0 ? parseFloat(priceMatches[0].replace('R$','').replace(/\./g,'').replace(',','.').trim()) : 0;

                            const name = extractName(fullText, '');
                            if (commission > 0 && name.length > 5) {
                                seen.add(href);
                                results.push({ name, url: href, commission, price });
                            }
                        } catch(e) {}
                    });

                    // ── Estratégia B: via imagens de produto (img dentro de links) ─
                    if (results.length === 0) {
                        const imgs = Array.from(document.querySelectorAll('img[src*="shopee"], img[src*="spx"], img[src*="cf.shopee"]'));
                        imgs.forEach(img => {
                            try {
                                const card = findCard(img, 10);
                                if (!card) return;

                                const fullText = card.innerText || '';
                                const productLinks = Array.from(card.querySelectorAll('a'))
                                    .filter(a => isProductUrl(a.href));
                                const href = productLinks.length > 0 ? productLinks[0].href : '';
                                if (!href || seen.has(href)) return;

                                const commMatches = fullText.match(/(\\d+(?:[,.]\\d+)?)\\s*%/g) || [];
                                const commValues = commMatches.map(m => parseFloat(m.replace('%','').replace(',','.')))
                                    .filter(v => v > 0 && v <= 80);
                                const commission = commValues.length > 0 ? Math.max(...commValues) : 0;

                                const priceMatches2 = fullText.match(/R\$\s?[\d.,]+/g) || [];
                                const price2 = priceMatches2.length > 0 ? parseFloat(priceMatches2[0].replace('R$','').replace(/\./g,'').replace(',','.').trim()) : 0;

                                const name = extractName(fullText, img.alt || '');
                                if (commission > 0 && name.length > 5) {
                                    seen.add(href);
                                    results.push({ name, url: href, commission, price: price2 });
                                }
                            } catch(e) {}
                        });
                    }

                    // ── Debug info ─────────────────────────────────────────────
                    const debugInfo = {
                        totalButtons: document.querySelectorAll('button').length,
                        obterLinkBtns: Array.from(document.querySelectorAll('button')).filter(b => /obter\\s*link/i.test(b.textContent)).length,
                        shopeeLinks: document.querySelectorAll('a[href*="shopee.com.br"]').length,
                        bodyTextLen: document.body.innerText.length,
                    };
                    console.log('DEBUG EXTRACT:', JSON.stringify(debugInfo));

                    return results;
                }
            """)

            logger.info(f"JS extraiu {len(js_products)} produtos na página {page_num}")

            # Se ainda 0, tira screenshot e loga HTML parcial para debug
            if len(js_products) == 0:
                await _screenshot(page, f"zero_products_p{page_num}", screenshots_dir)
                page_title = await page.title()
                logger.warning(f"0 produtos extraídos. Título da página: '{page_title}' | URL: {page.url}")

                # Tenta aguardar elemento de produto aparecer (até 10s)
                try:
                    await page.wait_for_selector("button", timeout=10000)
                    btn_count = await page.evaluate("document.querySelectorAll('button').length")
                    logger.info(f"Botões na página: {btn_count}")
                    obter_count = await page.evaluate("""
                        Array.from(document.querySelectorAll('button'))
                            .filter(b => /obter\\s*link/i.test(b.textContent)).length
                    """)
                    logger.info(f"Botões 'Obter link': {obter_count}")
                except Exception:
                    pass

                logger.warning("Nenhum produto encontrado nesta página. Encerrando paginação.")
                break

            for p in js_products:
                if len(products) >= max_products:
                    break
                commission = p.get('commission', 0)
                if commission < min_commission_pct:
                    continue
                url = p.get('url', '')
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                products.append({
                    "produto": p.get('name', 'Produto'),
                    "product_id": _extract_product_id(url),
                    "link_original": url,
                    "comissao_novo": commission,
                    "comissao_atual": commission * 0.5,
                    "preco": p.get('price', 0),
                    "thumbnail_url": "",
                    "category": "",
                })

            if len(products) >= max_products:
                break

            # Paginação — tenta botão primeiro, senão usa scroll infinito
            next_btn = await page.query_selector(SELECTORS["pagination_next"])
            if next_btn:
                is_disabled = await next_btn.get_attribute("disabled")
                if is_disabled:
                    logger.info("Botão próxima página desabilitado, fim.")
                    break
                await next_btn.click()
                await _delay(3, 5)
                page_num += 1
            else:
                # Scroll infinito — rola até o fim e aguarda novos produtos carregarem
                btn_before = await page.evaluate("""
                    () => Array.from(document.querySelectorAll('button'))
                        .filter(b => /obter\\s*link/i.test(b.textContent)).length
                """)
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await _delay(3, 5)
                btn_after = await page.evaluate("""
                    () => Array.from(document.querySelectorAll('button'))
                        .filter(b => /obter\\s*link/i.test(b.textContent)).length
                """)
                if btn_after <= btn_before:
                    logger.info("Scroll infinito: sem novos produtos, fim da listagem.")
                    break
                logger.info(f"Scroll infinito: {btn_before} → {btn_after} botões, continuando...")
                page_num += 1

    except Exception as e:
        logger.error(f"Erro ao descobrir produtos na seção: {e}")
        await _screenshot(page, "discover_error", screenshots_dir)


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
    # Novo formato: affiliate.shopee.com.br/offer/product_offer/ID
    match = re.search(r"/offer/product_offer/(\d+)", url)
    if match:
        return match.group(1)
    # Formato clássico: -i.SHOPID.ITEMID
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
    Fills SubID fields with tracking data using JS to avoid selector issues.
    """
    try:
        await page.goto(
            f"{affiliate_url}/offer/custom_link",
            wait_until="networkidle",
            timeout=30000,
        )
        await _delay(2, 3)

        subid_values = [
            subids.get("nome_do_produto", ""),
            subids.get("rede_social", ""),
            subids.get("campanha_atual", ""),
        ]

        # Usa JS para preencher todos os campos de forma robusta
        filled = await page.evaluate("""
            ([url, sub1, sub2, sub3]) => {
                // Preenche a textarea com a URL do produto
                const textarea = document.querySelector('textarea');
                if (!textarea) return {ok: false, reason: 'textarea nao encontrada'};
                const nativeTextareaSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
                nativeTextareaSetter.call(textarea, url);
                textarea.dispatchEvent(new Event('input', {bubbles: true}));
                textarea.dispatchEvent(new Event('change', {bubbles: true}));

                // Preenche os 3 campos Sub_id (inputs de texto)
                const inputs = Array.from(document.querySelectorAll('input[type="text"], input:not([type])'))
                    .filter(i => !i.readOnly && i.offsetParent !== null);
                const nativeInputSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                const subValues = [sub1, sub2, sub3];
                for (let i = 0; i < Math.min(inputs.length, 3); i++) {
                    nativeInputSetter.call(inputs[i], subValues[i]);
                    inputs[i].dispatchEvent(new Event('input', {bubbles: true}));
                    inputs[i].dispatchEvent(new Event('change', {bubbles: true}));
                }
                return {ok: true, inputsFound: inputs.length};
            }
        """, [product["link_original"]] + subid_values)

        logger.debug(f"Preenchimento do formulário: {filled}")
        await _delay(1, 2)

        # Clica no botão "Obter link"
        clicked = await page.evaluate("""
            () => {
                const btns = Array.from(document.querySelectorAll('button'))
                    .filter(b => /obter\\s*link/i.test(b.textContent) && !b.disabled);
                if (btns.length > 0) { btns[0].click(); return true; }
                return false;
            }
        """)
        if not clicked:
            logger.warning("Botão 'Obter link' não encontrado na página custom_link")
            await _screenshot(page, f"custom_link_no_btn_{product.get('product_id','x')}", screenshots_dir)
            return None

        await _delay(2, 3)

        # Captura o link gerado — tenta múltiplas estratégias
        link = await page.evaluate("""
            () => {
                // Estratégia 1: input readonly (campo de resultado)
                const readonly = document.querySelector('input[readonly]');
                if (readonly && readonly.value && readonly.value.startsWith('http')) return readonly.value;

                // Estratégia 2: qualquer input com URL de afiliado
                const inputs = Array.from(document.querySelectorAll('input'));
                for (const inp of inputs) {
                    if (inp.value && inp.value.includes('s.shopee') || (inp.value && inp.value.includes('shope') && inp.value.includes('sub_id'))) {
                        return inp.value;
                    }
                }

                // Estratégia 3: texto visível que contém link s.shopee
                const allText = document.body.innerText;
                const match = allText.match(/(https?:\\/\\/s\\.shopee\\.com\\.br\\/[\\w\\-]+)/);
                if (match) return match[1];

                return null;
            }
        """)

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
        current_url = page.url
        logger.info(
            "Modo CDP: %s | Página inicial: %s",
            "ATIVO" if _cdp_mode else "inativo (navegador próprio)",
            current_url,
        )

        # In CDP mode, skip login entirely when already on the affiliate domain.
        already_on_affiliate = (
            _cdp_mode
            and "affiliate.shopee.com.br" in current_url
            and "login" not in current_url
            and "404" not in current_url
        )

        if already_on_affiliate:
            logger.info(
                "CDP: já na página do afiliado — login ignorado, sessão considerada ativa."
            )
            logged_in = True
        else:
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
            try:
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
            except Exception as e:
                logger.warning(f"[{i+1}] Produto ignorado por erro: {product.get('produto', '?')[:50]} — {e}")
            finally:
                await _delay(1, 2)

        # ── Auto-follow dos vendedores (se habilitado) ────────────────────────
        auto_follow = getattr(settings, "auto_follow_sellers", True)
        if auto_follow and enriched:
            logger.info("Iniciando auto-follow dos vendedores...")
            try:
                from scraper.seller_follower import follow_sellers_from_products
                max_follows = getattr(settings, "max_follows_per_run", 50)
                follow_stats = await follow_sellers_from_products(
                    page=page,
                    products=enriched,
                    max_follows=max_follows,
                )
                logger.info(
                    f"Follow concluído: {follow_stats.get('seguido', 0)} novos | "
                    f"{follow_stats.get('ja_seguindo', 0)} já seguia"
                )
            except Exception as e:
                logger.warning(f"Auto-follow falhou (não crítico): {e}")

        return enriched

    finally:
        if _cdp_mode:
            # Em modo CDP não fechamos o Chrome do usuário — apenas desconectamos
            logger.info("Modo CDP: desconectando sem fechar o Chrome.")
            try:
                await playwright.stop()
            except Exception:
                pass
        else:
            await browser.close()
            await playwright.stop()
