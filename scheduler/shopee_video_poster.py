"""
Shopee Videos Poster — automação via Playwright CDP

Fluxo:
  1. Conecta ao Chrome já aberto (CDP porta 9222)
  2. Navega para a área de upload de vídeo do Shopee
  3. Faz upload do arquivo de vídeo
  4. Preenche título, descrição e link afiliado
  5. Publica ou agenda o post

URLs do Shopee Creator:
  - Shopee Video (afiliados): affiliate.shopee.com.br/video/upload
  - Shopee Seller Center: seller.shopee.com.br/portal/product/video
  - Feed criativo: affiliate.shopee.com.br/creative/feed

O bot tenta as 3 opções em sequência.
"""

import asyncio
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# URLs possíveis para upload de vídeo no Shopee (testadas em ordem)
SHOPEE_VIDEO_URLS = [
    "https://affiliate.shopee.com.br/video/upload",
    "https://affiliate.shopee.com.br/creative/video",
    "https://seller.shopee.com.br/portal/product/video",
]

# Seletores para o formulário de upload
UPLOAD_SELECTORS = {
    "file_input": "input[type='file'][accept*='video'], input[type='file']",
    "title": "input[placeholder*='título'], input[placeholder*='title'], input[placeholder*='Título']",
    "description": "textarea[placeholder*='descrição'], textarea[placeholder*='caption'], textarea[placeholder*='Descrição']",
    "submit": "button:has-text('Publicar'), button:has-text('Postar'), button:has-text('Submit'), button:has-text('Publish')",
    "success": "[class*='success'], [class*='published'], .upload-success",
}


async def _find_working_video_url(page) -> str | None:
    """Testa as URLs possíveis e retorna a primeira que funcionar."""
    for url in SHOPEE_VIDEO_URLS:
        try:
            await page.goto(url, wait_until="networkidle", timeout=15000)
            await asyncio.sleep(2)
            current = page.url
            # Se não redirecionou para login ou 404, a URL existe
            if "login" not in current and "404" not in current and "error" not in current:
                logger.info(f"URL de vídeo encontrada: {current}")
                return current
        except Exception:
            continue
    return None


async def post_shopee_video_async(
    product: dict,
    video_path: str,
    settings,
) -> dict:
    """
    Posta um vídeo no Shopee usando o Chrome já aberto via CDP.

    Returns:
        {"status": "success"} | {"status": "failed", "reason": "..."}
    """
    from playwright.async_api import async_playwright

    if not video_path or not Path(video_path).exists():
        logger.warning(f"Vídeo não encontrado: {video_path}")
        return {"status": "failed", "reason": "video_not_found"}

    playwright = await async_playwright().start()

    try:
        # Conecta ao Chrome existente via CDP
        try:
            browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = await context.new_page()
            logger.info("Shopee Video: conectado via CDP")
        except Exception:
            logger.info("CDP não disponível, abrindo novo Chrome...")
            browser = await playwright.chromium.launch(
                channel="chrome", headless=False,
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = await browser.new_context()

            # Carrega sessão salva se existir
            session_path = settings.SESSION_PATH
            if Path(session_path).exists():
                import json
                cookies = json.loads(Path(session_path).read_text()).get("cookies", [])
                await context.add_cookies(cookies)

            page = await context.new_page()

        # Encontra URL de upload funcional
        video_url = await _find_working_video_url(page)

        if not video_url:
            logger.error("Nenhuma URL de upload de vídeo disponível no Shopee.")
            await page.close()
            return {"status": "failed", "reason": "no_upload_url"}

        await asyncio.sleep(2)

        # ── Upload do arquivo de vídeo ────────────────────────────────────────
        file_input = await page.query_selector(UPLOAD_SELECTORS["file_input"])
        if not file_input:
            # Às vezes precisa clicar em uma área de drop para revelar o input
            drop_area = await page.query_selector("[class*='upload'], [class*='drop-zone'], .upload-area")
            if drop_area:
                await drop_area.click()
                await asyncio.sleep(1)
                file_input = await page.query_selector(UPLOAD_SELECTORS["file_input"])

        if file_input:
            await file_input.set_input_files(video_path)
            logger.info(f"Vídeo enviado para upload: {Path(video_path).name}")
            await asyncio.sleep(5)  # Aguarda processamento do upload
        else:
            logger.error("Input de arquivo não encontrado na página de vídeo")
            await page.close()
            return {"status": "failed", "reason": "no_file_input"}

        # ── Aguarda upload processar (barra de progresso desaparecer) ─────────
        try:
            await page.wait_for_selector(
                "[class*='progress']:not([style*='100']), .upload-progress",
                state="hidden",
                timeout=120000  # 2 min para upload
            )
        except Exception:
            await asyncio.sleep(15)  # Fallback: aguarda 15s

        # ── Preenche título (overlay do vídeo) ────────────────────────────────
        title = product.get("overlay", product.get("produto", ""))[:100]
        title_input = await page.query_selector(UPLOAD_SELECTORS["title"])
        if title_input:
            await title_input.fill(title)
            await asyncio.sleep(0.5)
            logger.debug(f"Título preenchido: {title[:50]}")

        # ── Preenche descrição (legenda + hashtags + link) ────────────────────
        legenda = product.get("legenda", "")
        hashtags = product.get("hashtags", "")
        link = product.get("link_afiliado", product.get("link_original", ""))
        caption = f"{legenda}\n\n{hashtags}\n\n🔗 {link}"[:2000]

        desc_input = await page.query_selector(UPLOAD_SELECTORS["description"])
        if desc_input:
            await desc_input.fill(caption)
            await asyncio.sleep(0.5)
            logger.debug("Descrição preenchida")

        # ── Adiciona link de produto (se houver campo específico) ─────────────
        try:
            link_field = await page.query_selector(
                "input[placeholder*='link'], input[placeholder*='url'], input[placeholder*='produto']"
            )
            if link_field:
                await link_field.fill(link)
                await asyncio.sleep(0.5)
        except Exception:
            pass

        # ── Clica em Publicar ─────────────────────────────────────────────────
        submitted = await page.evaluate("""
            () => {
                const btns = Array.from(document.querySelectorAll('button'))
                    .filter(b => /publicar|postar|publish|submit/i.test(b.textContent) && !b.disabled);
                if (btns.length > 0) { btns[0].click(); return btns[0].textContent.trim(); }
                return null;
            }
        """)

        if submitted:
            logger.info(f"Botão '{submitted}' clicado — aguardando confirmação...")
            await asyncio.sleep(8)

            # Verifica se foi publicado com sucesso
            success = await page.query_selector(UPLOAD_SELECTORS["success"])
            if success:
                logger.info(f"✅ Shopee Video publicado: {product.get('produto', '')[:50]}")
                await page.close()
                return {"status": "success"}

            # Verifica se URL mudou (indicando sucesso)
            if "success" in page.url or "published" in page.url:
                logger.info(f"✅ Shopee Video publicado (via URL): {product.get('produto', '')[:50]}")
                await page.close()
                return {"status": "success"}

            # Tira screenshot para debug
            try:
                screenshots_dir = getattr(settings, "SCREENSHOTS_DIR", "logs/screenshots")
                Path(screenshots_dir).mkdir(parents=True, exist_ok=True)
                await page.screenshot(path=f"{screenshots_dir}/shopee_video_after_submit.png")
            except Exception:
                pass

            logger.warning("Publicação enviada mas confirmação não detectada. Verifique o Chrome.")
            await page.close()
            return {"status": "success", "note": "posted_unconfirmed"}
        else:
            logger.error("Botão de publicar não encontrado")
            await page.close()
            return {"status": "failed", "reason": "no_submit_button"}

    except Exception as e:
        logger.error(f"Erro ao postar Shopee Video: {e}")
        return {"status": "failed", "reason": str(e)}
    finally:
        try:
            await playwright.stop()
        except Exception:
            pass


def post_shopee_video(product: dict, video_path: str, settings) -> dict:
    """Wrapper síncrono para uso no scheduler."""
    return asyncio.run(post_shopee_video_async(product, video_path, settings))


# ── Scanner de vídeos ──────────────────────────────────────────────────────────

def find_video_for_product(product: dict, videos_dir: str = "data/videos") -> str | None:
    """
    Busca um vídeo na pasta data/videos/ que corresponda ao produto.

    Convenção de nome do arquivo:
      - Qualquer .mp4, .mov, .avi na pasta (pega o mais recente não usado)
      - Ou arquivo com nome similar ao produto

    Returns: caminho absoluto do vídeo, ou None
    """
    videos_path = Path(videos_dir)
    if not videos_path.exists():
        videos_path.mkdir(parents=True, exist_ok=True)
        return None

    # Extensões de vídeo aceitas
    extensions = [".mp4", ".mov", ".avi", ".webm", ".mkv"]
    videos = []
    for ext in extensions:
        videos.extend(videos_path.glob(f"*{ext}"))

    if not videos:
        return None

    # Tenta encontrar vídeo com nome similar ao produto
    product_name = product.get("produto", "").lower()
    keywords = [w for w in product_name.split() if len(w) > 3]

    for video in sorted(videos, key=lambda v: v.stat().st_mtime, reverse=True):
        video_name = video.stem.lower()
        if any(kw in video_name for kw in keywords):
            logger.info(f"Vídeo encontrado por nome: {video.name}")
            return str(video)

    # Fallback: pega o vídeo mais recente não marcado como usado
    for video in sorted(videos, key=lambda v: v.stat().st_mtime, reverse=True):
        if not video.stem.endswith("_used"):
            logger.info(f"Vídeo mais recente: {video.name}")
            return str(video)

    return None


def mark_video_as_used(video_path: str):
    """Renomeia o vídeo adicionando _used para não reutilizar."""
    if not video_path:
        return
    path = Path(video_path)
    if path.exists() and not path.stem.endswith("_used"):
        new_name = path.parent / f"{path.stem}_used{path.suffix}"
        try:
            path.rename(new_name)
            logger.info(f"Vídeo marcado como usado: {new_name.name}")
        except Exception as e:
            logger.warning(f"Não foi possível renomear vídeo: {e}")
