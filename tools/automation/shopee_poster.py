"""Posta um video no Shopee Videos via Chrome local (CDP), com CONFIRMACAO REAL.

O bot antigo, quando nao conseguia confirmar a publicacao, retornava
{"status": "success", "note": "posted_unconfirmed"} -- ou seja, fingia sucesso.
Aqui isso nunca acontece: se nao for possivel confirmar de verdade, o resultado
e sempre `confirmed=False`, para a campanha ser marcada como `needs_review` em
vez de `posted`.
"""

import asyncio
from pathlib import Path

SHOPEE_VIDEO_URLS = [
    "https://affiliate.shopee.com.br/video/upload",
    "https://affiliate.shopee.com.br/creative/video",
]

SELECTORS = {
    "file_input": "input[type='file'][accept*='video'], input[type='file']",
    "title": "input[placeholder*='título'], input[placeholder*='title'], input[placeholder*='Título']",
    "description": "textarea[placeholder*='descrição'], textarea[placeholder*='caption'], textarea[placeholder*='Descrição']",
}


async def _achar_url_de_upload(page) -> str | None:
    for url in SHOPEE_VIDEO_URLS:
        try:
            await page.goto(url, wait_until="networkidle", timeout=15000)
            await asyncio.sleep(2)
            current = page.url
            if "login" not in current and "404" not in current:
                return current
        except Exception:
            continue
    return None


async def postar_video_async(
    nome_produto: str,
    video_path: str,
    legenda: str,
    hashtags: str,
    link_afiliado: str,
) -> dict:
    """Tenta postar o video no Shopee Videos. So retorna confirmed=True se
    de fato confirmar a publicacao (toast de sucesso, URL do post resultante,
    ou o video aparecendo na lista de videos do usuario)."""
    from playwright.async_api import async_playwright

    if not video_path or not Path(video_path).exists():
        return {"confirmed": False, "post_url": None, "detalhe": "arquivo de video nao encontrado"}

    playwright = await async_playwright().start()
    try:
        try:
            browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
        except Exception:
            return {
                "confirmed": False,
                "post_url": None,
                "detalhe": "Chrome CDP nao disponivel na porta 9222 -- abra o Chrome com "
                "--remote-debugging-port=9222 e logue em affiliate.shopee.com.br",
            }

        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await context.new_page()

        upload_url = await _achar_url_de_upload(page)
        if not upload_url:
            await page.close()
            return {"confirmed": False, "post_url": None, "detalhe": "pagina de upload de video nao encontrada"}

        await asyncio.sleep(2)

        file_input = await page.query_selector(SELECTORS["file_input"])
        if not file_input:
            await page.close()
            return {"confirmed": False, "post_url": None, "detalhe": "campo de upload de arquivo nao encontrado"}

        await file_input.set_input_files(video_path)
        await asyncio.sleep(5)

        title_input = await page.query_selector(SELECTORS["title"])
        if title_input:
            await title_input.fill(nome_produto[:100])

        caption = f"{legenda}\n\n{hashtags}\n\n{link_afiliado}"[:2000]
        desc_input = await page.query_selector(SELECTORS["description"])
        if desc_input:
            await desc_input.fill(caption)

        await asyncio.sleep(1)

        clicked_label = await page.evaluate(
            """
            () => {
                const btns = Array.from(document.querySelectorAll('button'))
                    .filter(b => /publicar|postar|publish|submit/i.test(b.textContent) && !b.disabled);
                if (btns.length > 0) { btns[0].click(); return btns[0].textContent.trim(); }
                return null;
            }
            """
        )
        if not clicked_label:
            await page.close()
            return {"confirmed": False, "post_url": None, "detalhe": "botao de publicar nao encontrado"}

        await asyncio.sleep(8)

        # Confirmacao real: precisa de UM dos sinais abaixo. Sem isso, e needs_review.
        url_apos_publicar = page.url
        if url_apos_publicar != upload_url and (
            "success" in url_apos_publicar or "/video/" in url_apos_publicar or "/post/" in url_apos_publicar
        ):
            await page.close()
            return {"confirmed": True, "post_url": url_apos_publicar, "detalhe": "URL mudou apos publicar"}

        success_el = await page.query_selector("[class*='success'], [class*='published']")
        if success_el:
            await page.close()
            return {"confirmed": True, "post_url": url_apos_publicar, "detalhe": "elemento de sucesso detectado"}

        await page.close()
        return {
            "confirmed": False,
            "post_url": None,
            "detalhe": f"botao '{clicked_label}' foi clicado mas nenhuma confirmacao real foi detectada "
            "(nem mudanca de URL, nem elemento de sucesso) -- verifique manualmente",
        }

    finally:
        await playwright.stop()


def postar_video(nome_produto: str, video_path: str, legenda: str, hashtags: str, link_afiliado: str) -> dict:
    return asyncio.run(postar_video_async(nome_produto, video_path, legenda, hashtags, link_afiliado))
