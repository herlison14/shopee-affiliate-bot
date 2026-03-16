"""
Notifier: envia mensagens de WhatsApp via WhatsApp Web (Chrome CDP)
com o copy gerado para cada produto pronto para postar.
"""

import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


async def _send_whatsapp_via_cdp(phone: str, message: str) -> bool:
    """
    Abre WhatsApp Web via Chrome CDP e envia mensagem para o número.
    phone: formato internacional sem + (ex: 5511999999999)
    """
    from playwright.async_api import async_playwright

    url = f"https://web.whatsapp.com/send?phone={phone}&text={_url_encode(message)}&app_absent=0"

    try:
        playwright = await async_playwright().start()
        try:
            browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = await context.new_page()
        except Exception:
            # Fallback: abre novo Chrome
            browser = await playwright.chromium.launch(
                channel="chrome", headless=False,
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = await browser.new_context()
            page = await context.new_page()

        await page.goto(url, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(5)

        # Aguarda o botão de enviar aparecer (WhatsApp Web carregado)
        try:
            # Tenta clicar no botão de enviar
            send_btn = await page.wait_for_selector(
                "button[data-testid='compose-btn-send'], span[data-icon='send']",
                timeout=20000
            )
            if send_btn:
                await send_btn.click()
                await asyncio.sleep(2)
                logger.info(f"WhatsApp enviado para {phone}")
                await page.close()
                return True
        except Exception as e:
            logger.warning(f"Botão de envio não encontrado: {e}")
            # Tenta pressionar Enter como fallback
            await page.keyboard.press("Enter")
            await asyncio.sleep(2)
            await page.close()
            return True

    except Exception as e:
        logger.error(f"Erro ao enviar WhatsApp: {e}")
        return False
    finally:
        try:
            await playwright.stop()
        except Exception:
            pass


def _url_encode(text: str) -> str:
    """URL encode para WhatsApp Web."""
    import urllib.parse
    return urllib.parse.quote(text)


def _format_product_message(product: dict, idx: int, total: int) -> str:
    """Formata a mensagem do produto para WhatsApp."""
    nome = product.get("produto", "Produto")[:50]
    comissao = product.get("comissao_novo", 0)
    overlay = product.get("overlay", "")
    legenda = product.get("legenda", "")
    hashtags = product.get("hashtags", "")
    link = product.get("link_afiliado", product.get("link_original", ""))

    return f"""🛒 *PRODUTO {idx}/{total} PRONTO PARA POSTAR*

📦 *{nome}*
💰 Comissão: {comissao:.1f}%

🎬 *OVERLAY (texto no vídeo):*
{overlay}

📝 *LEGENDA:*
{legenda}

#️⃣ *HASHTAGS:*
{hashtags}

🔗 *LINK AFILIADO:*
{link}

⏰ Gerado: {datetime.now().strftime('%d/%m %H:%M')}
"""


def _format_summary_message(products: list) -> str:
    """Mensagem resumo com todos os produtos."""
    lines = [f"✅ *{len(products)} PRODUTOS PRONTOS PARA POSTAR!*\n"]
    for i, p in enumerate(products, 1):
        nome = p.get("produto", "Produto")[:40]
        comissao = p.get("comissao_novo", 0)
        lines.append(f"{i}. {nome} — {comissao:.1f}%")
    lines.append(f"\n🕐 {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    lines.append("📊 Veja o dashboard: http://localhost:8501")
    return "\n".join(lines)


def notify_products_ready(products: list, phone: str, max_messages: int = 5):
    """
    Envia notificação WhatsApp quando produtos estão prontos.
    Envia 1 mensagem resumo + até max_messages individuais com copy completo.
    """
    if not products or not phone:
        logger.warning("Sem produtos ou número de WhatsApp configurado.")
        return

    logger.info(f"Enviando {min(len(products), max_messages+1)} mensagens WhatsApp para {phone}")

    # Mensagem resumo
    summary = _format_summary_message(products)
    asyncio.run(_send_whatsapp_via_cdp(phone, summary))
    time.sleep(3)

    # Mensagens individuais (até max_messages)
    for i, product in enumerate(products[:max_messages], 1):
        msg = _format_product_message(product, i, min(len(products), max_messages))
        success = asyncio.run(_send_whatsapp_via_cdp(phone, msg))
        if success:
            logger.info(f"Notificação {i}/{min(len(products), max_messages)} enviada.")
        time.sleep(4)  # Pausa entre mensagens


def notify_simple(message: str, phone: str):
    """Envia uma mensagem simples de texto no WhatsApp."""
    if not phone:
        return
    asyncio.run(_send_whatsapp_via_cdp(phone, message))
