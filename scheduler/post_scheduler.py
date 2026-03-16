"""
Post Scheduler: APScheduler + TikTok Content Posting API + Shopee Videos automation.

TikTok posting requires a video file. Two modes:
  Mode A (video file available): Posts automatically.
  Mode B (no video): Writes to a "ready_to_post" queue for manual posting.
"""

import asyncio
import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path

import httpx
import pandas as pd
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

TIKTOK_API_BASE = "https://open.tiktokapis.com/v2"
MAX_TIKTOK_CAPTION = 2200


# ── Excel helpers ─────────────────────────────────────────────────────────────

def _read_pending_products(excel_path: str, excel_lock: threading.Lock, limit: int = 1) -> list:
    """Read products with status_agendamento == 'pendente'."""
    with excel_lock:
        try:
            df = pd.read_excel(excel_path, engine="openpyxl")
            pending = df[df["status_agendamento"] == "pendente"].head(limit)
            return pending.to_dict("records")
        except FileNotFoundError:
            logger.warning("output.xlsx não encontrado. Pipeline ainda não foi executado?")
            return []
        except Exception as e:
            logger.error(f"Erro ao ler Excel: {e}")
            return []


def _update_post_status(
    excel_path: str,
    excel_lock: threading.Lock,
    link_original: str,
    status: str,
    platform: str = "",
):
    """Update a product row's scheduling status in the Excel file."""
    with excel_lock:
        try:
            df = pd.read_excel(excel_path, engine="openpyxl")
            mask = df["link_original"] == link_original
            df.loc[mask, "status_agendamento"] = status
            df.loc[mask, "data_publicacao"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            df.to_excel(excel_path, index=False, engine="openpyxl")
            logger.info(f"Status atualizado: {status} — {link_original[:60]}")
        except Exception as e:
            logger.error(f"Erro ao atualizar Excel: {e}")


# ── TikTok Content Posting API ─────────────────────────────────────────────────

def _build_caption(product: dict) -> str:
    caption = f"{product.get('legenda', '')}\n\n{product.get('hashtags', '')}"
    return caption[:MAX_TIKTOK_CAPTION]


def _refresh_tiktok_token(refresh_token: str, client_key: str = "", client_secret: str = "") -> str | None:
    """Attempt to refresh TikTok access token. Returns new token or None."""
    try:
        resp = httpx.post(
            "https://open.tiktokapis.com/v2/oauth/token/",
            data={
                "client_key": client_key,
                "client_secret": client_secret,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            timeout=15,
        )
        data = resp.json()
        return data.get("access_token")
    except Exception as e:
        logger.error(f"Falha ao renovar token TikTok: {e}")
        return None


def post_to_tiktok(product: dict, video_path: str, access_token: str, open_id: str) -> dict:
    """
    Post a video to TikTok using Content Posting API v2.
    Returns {"status": "success", "publish_id": ...} or {"status": "failed", "error": ...}
    """
    if not video_path or not Path(video_path).exists():
        logger.warning(f"Vídeo não encontrado: {video_path}. Adicionando à fila manual.")
        return {"status": "fila_manual", "reason": "video_not_found"}

    caption = _build_caption(product)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    # Step 1: Initialize upload
    try:
        video_size = Path(video_path).stat().st_size
        init_payload = {
            "post_info": {
                "title": caption,
                "privacy_level": "PUBLIC_TO_EVERYONE",
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": video_size,
                "chunk_size": video_size,
                "total_chunk_count": 1,
            },
        }
        resp = httpx.post(
            f"{TIKTOK_API_BASE}/post/publish/video/init/",
            headers=headers,
            json=init_payload,
            timeout=30,
        )
        if resp.status_code == 401:
            return {"status": "failed", "error": "token_expired"}
        if resp.status_code != 200:
            return {"status": "failed", "error": f"init_http_{resp.status_code}"}

        data = resp.json().get("data", {})
        upload_url = data.get("upload_url")
        publish_id = data.get("publish_id")

        if not upload_url or not publish_id:
            return {"status": "failed", "error": "missing_upload_url_or_publish_id"}

    except Exception as e:
        return {"status": "failed", "error": str(e)}

    # Step 2: Upload video
    try:
        with open(video_path, "rb") as f:
            video_data = f.read()
        upload_headers = {
            "Content-Type": "video/mp4",
            "Content-Range": f"bytes 0-{video_size - 1}/{video_size}",
            "Content-Length": str(video_size),
        }
        upload_resp = httpx.put(upload_url, content=video_data, headers=upload_headers, timeout=120)
        if upload_resp.status_code not in (200, 206):
            return {"status": "failed", "error": f"upload_http_{upload_resp.status_code}"}
    except Exception as e:
        return {"status": "failed", "error": f"upload_exception: {e}"}

    # Step 3: Poll for publish completion
    for _ in range(10):
        time.sleep(5)
        try:
            status_resp = httpx.post(
                f"{TIKTOK_API_BASE}/post/publish/status/fetch/",
                headers=headers,
                json={"publish_id": publish_id},
                timeout=15,
            )
            status_data = status_resp.json().get("data", {})
            pub_status = status_data.get("status", "")
            if pub_status == "PUBLISH_COMPLETE":
                logger.info(f"TikTok publicado com sucesso. ID: {publish_id}")
                return {"status": "success", "publish_id": publish_id}
            if pub_status in ("FAILED", "SPAM_RISK_USER_REFUSED"):
                return {"status": "failed", "error": f"tiktok_status: {pub_status}"}
        except Exception as e:
            logger.warning(f"Erro ao verificar status TikTok: {e}")

    return {"status": "failed", "error": "publish_timeout"}


# ── Shopee Videos automation ───────────────────────────────────────────────────

async def post_to_shopee_videos_async(
    product: dict,
    video_path: str,
    settings,
) -> bool:
    """Post a video to Shopee Videos via browser automation."""
    from playwright.async_api import async_playwright

    if not video_path or not Path(video_path).exists():
        logger.warning(f"Vídeo não encontrado para Shopee: {video_path}")
        return False

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=settings.headless)
        context = await browser.new_context()

        # Load existing session
        session_path = settings.SESSION_PATH
        if Path(session_path).exists():
            import json as _json
            cookies = _json.loads(Path(session_path).read_text()).get("cookies", [])
            await context.add_cookies(cookies)

        page = await context.new_page()
        try:
            await page.goto(
                f"{settings.shopee_affiliate_url}/video/upload",
                wait_until="networkidle",
                timeout=30000,
            )

            # Upload video file
            file_input = await page.query_selector("input[type='file']")
            if file_input:
                await file_input.set_input_files(video_path)
                await asyncio.sleep(3)

            # Fill title (overlay)
            title_input = await page.query_selector("input[placeholder*='título'], input[placeholder*='title']")
            if title_input:
                await title_input.fill(product.get("overlay", "")[:100])
                await asyncio.sleep(0.5)

            # Fill description (legenda)
            desc_input = await page.query_selector("textarea[placeholder*='descrição'], textarea[placeholder*='caption']")
            if desc_input:
                caption = f"{product.get('legenda', '')}\n{product.get('hashtags', '')}"
                await desc_input.fill(caption[:2000])
                await asyncio.sleep(0.5)

            # Submit
            submit_btn = await page.query_selector("button:has-text('Publicar'), button:has-text('Submit')")
            if submit_btn:
                await submit_btn.click()
                await asyncio.sleep(5)
                logger.info(f"Shopee Video enviado: {product.get('produto', '')}")
                return True

        except Exception as e:
            logger.error(f"Erro ao postar Shopee Video: {e}")
        finally:
            await browser.close()

    return False


def post_to_shopee_videos(product: dict, video_path: str, settings) -> bool:
    """Sync wrapper for async Shopee Videos posting."""
    return asyncio.run(post_to_shopee_videos_async(product, video_path, settings))


# ── Manual queue (Mode B — no video file) ──────────────────────────────────────

def write_manual_queue(product: dict, queue_path: str = "data/manual_queue.json"):
    """Write product to manual posting queue when no video file is available."""
    Path(queue_path).parent.mkdir(parents=True, exist_ok=True)
    queue = []
    if Path(queue_path).exists():
        try:
            queue = json.loads(Path(queue_path).read_text())
        except Exception:
            pass

    queue.append({
        "produto": product.get("produto"),
        "overlay": product.get("overlay"),
        "legenda": product.get("legenda"),
        "hashtags": product.get("hashtags"),
        "link_afiliado": product.get("link_afiliado"),
        "adicionado_em": datetime.now().isoformat(),
    })
    Path(queue_path).write_text(json.dumps(queue, ensure_ascii=False, indent=2))
    logger.info(f"Adicionado à fila manual: {product.get('produto', '')}")


# ── APScheduler ────────────────────────────────────────────────────────────────

def dispatch_post_job(settings, excel_lock: threading.Lock):
    """Called by APScheduler at each scheduled time."""
    logger.info("=" * 50)
    logger.info(f"Scheduler: executando job — {datetime.now().strftime('%d/%m %H:%M')}")

    # 1) Roda o pipeline completo (scraping + copy IA)
    try:
        import subprocess, sys
        logger.info("Iniciando pipeline automatico...")
        result = subprocess.run(
            [sys.executable, "main.py"],
            capture_output=True, text=True, timeout=1800,  # 30 min timeout
            cwd=str(Path(__file__).parent.parent)
        )
        if result.returncode == 0:
            logger.info("Pipeline executado com sucesso!")
        else:
            logger.error(f"Pipeline falhou: {result.stderr[-500:]}")
    except subprocess.TimeoutExpired:
        logger.error("Pipeline timeout (30 min). Abortando.")
        return
    except Exception as e:
        logger.error(f"Erro ao rodar pipeline: {e}")

    # 2) Lê produtos pendentes para postar
    whatsapp_phone = getattr(settings, "whatsapp_phone", "")
    products = _read_pending_products(settings.EXCEL_PATH, excel_lock, limit=10)

    if not products:
        logger.info("Nenhum produto pendente para postar.")
        return

    logger.info(f"{len(products)} produtos prontos.")

    # 3) Notificação WhatsApp com copy pronto
    if whatsapp_phone:
        try:
            from scheduler.notifier import notify_products_ready
            logger.info(f"Enviando notificação WhatsApp para {whatsapp_phone}...")
            notify_products_ready(products, whatsapp_phone, max_messages=5)
        except Exception as e:
            logger.error(f"Falha na notificação WhatsApp: {e}")

    # 4) Tentativa de postagem automática (se tokens disponíveis)
    for product in products:
        video_path = product.get("video_path", "")

        posted = False

        # TikTok (só se tiver token)
        if settings.social_network in ("tiktok", "all") and settings.tiktok_access_token:
            result = post_to_tiktok(
                product=product,
                video_path=video_path,
                access_token=settings.tiktok_access_token,
                open_id=settings.tiktok_open_id,
            )
            if result["status"] == "success":
                _update_post_status(
                    settings.EXCEL_PATH, excel_lock,
                    product["link_original"], "publicado_tiktok", "tiktok"
                )
                posted = True
                if whatsapp_phone:
                    try:
                        from scheduler.notifier import notify_simple
                        nome = product.get("produto", "Produto")[:40]
                        notify_simple(f"✅ *POSTADO NO TIKTOK!*\n{nome}", whatsapp_phone)
                    except Exception:
                        pass
            elif result["status"] == "failed" and result.get("error") == "token_expired":
                logger.warning("Token TikTok expirado. Configure TIKTOK_ACCESS_TOKEN no .env")
                _update_post_status(
                    settings.EXCEL_PATH, excel_lock,
                    product["link_original"], "fila_manual", "tiktok"
                )
                write_manual_queue(product)
            else:
                logger.error(f"TikTok falhou: {result}")
                _update_post_status(
                    settings.EXCEL_PATH, excel_lock,
                    product["link_original"], "falhou_tiktok", "tiktok"
                )

        # ── Shopee Videos (browser automation via CDP) ──────────────────────
        if not posted:
            from scheduler.shopee_video_poster import (
                post_shopee_video, find_video_for_product, mark_video_as_used
            )

            # Busca vídeo automaticamente na pasta data/videos/
            if not video_path:
                video_path = find_video_for_product(product, "data/videos") or ""

            if video_path:
                logger.info(f"Postando no Shopee Videos: {Path(video_path).name}")
                shopee_result = post_shopee_video(product, video_path, settings)

                if shopee_result["status"] == "success":
                    _update_post_status(
                        settings.EXCEL_PATH, excel_lock,
                        product["link_original"], "publicado_shopee", "shopee_videos"
                    )
                    mark_video_as_used(video_path)
                    posted = True

                    if whatsapp_phone:
                        try:
                            from scheduler.notifier import notify_simple
                            nome = product.get("produto", "Produto")[:40]
                            notify_simple(f"✅ *POSTADO NO SHOPEE!*\n📦 {nome}", whatsapp_phone)
                        except Exception:
                            pass
                else:
                    reason = shopee_result.get("reason", "desconhecido")
                    logger.error(f"Shopee Video falhou: {reason}")
                    _update_post_status(
                        settings.EXCEL_PATH, excel_lock,
                        product["link_original"], "falhou_shopee", "shopee_videos"
                    )

        # ── Fila manual: copy pronto, usuário grava e posta ──────────────────
        if not posted:
            write_manual_queue(product)
            _update_post_status(
                settings.EXCEL_PATH, excel_lock,
                product["link_original"], "fila_manual", ""
            )
            logger.info(f"✍️ Copy na fila manual: {product.get('produto', '')[:50]}")


def create_and_start_scheduler(settings, excel_lock: threading.Lock) -> BackgroundScheduler:
    """Create and start the APScheduler with configured post times."""
    scheduler = BackgroundScheduler(timezone="America/Sao_Paulo")

    for time_str in settings.post_times:
        try:
            hour, minute = time_str.split(":")
            scheduler.add_job(
                func=dispatch_post_job,
                trigger=CronTrigger(hour=int(hour), minute=int(minute)),
                args=[settings, excel_lock],
                id=f"post_job_{time_str.replace(':', '')}",
                replace_existing=True,
            )
            logger.info(f"Job agendado: {time_str} (America/Sao_Paulo)")
        except Exception as e:
            logger.error(f"Erro ao agendar {time_str}: {e}")

    scheduler.start()
    logger.info(f"Scheduler iniciado com {len(settings.post_times)} horários.")
    return scheduler
