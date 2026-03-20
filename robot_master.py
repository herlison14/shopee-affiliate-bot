"""
Shopee Affiliate Bot — Pipeline Direto
Fluxo: scrapa produto -> gera copy -> baixa video -> posta -> proximo

Sem agendador. Sem Excel como fila.
Cada produto e processado e postado imediatamente apos ser coletado.

Uso:
  python robot_master.py              # roda uma vez e para
  python robot_master.py --loop       # repete a cada CYCLE_HOURS horas
  python robot_master.py --virais     # so repost de virais
  python robot_master.py --tudo       # produtos + virais
"""

import argparse
import asyncio
import json
import logging
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

# ── Configuracoes ─────────────────────────────────────────────────────────────
TOP_PRODUTOS      = 5     # produtos por ciclo
TOP_VIRAIS        = 5     # virais por ciclo
DELAY_ENTRE_POSTS = 600   # segundos entre posts (10 min) — respeita rate limit
MIN_VIRAL_VIEWS   = 300
MIN_VIRAL_SCORE   = 15.0
CYCLE_HOURS       = 6     # intervalo entre ciclos no modo --loop

STATE_PATH = Path("data/robot_state.json")

# ── Logging ───────────────────────────────────────────────────────────────────
Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/robot_master.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


# ── Estado persistido (para o dashboard ler) ──────────────────────────────────

def _salvar_estado(estado: dict):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    estado["atualizado"] = datetime.now().isoformat()
    STATE_PATH.write_text(json.dumps(estado, ensure_ascii=False, indent=2), "utf-8")


def _estado_inicial() -> dict:
    return {
        "status": "iniciando",
        "ciclo_atual": 0,
        "ultimo_ciclo": None,
        "proximo_ciclo": None,
        "produtos_postados_total": 0,
        "virais_repostados_total": 0,
        "erros_total": 0,
        "ultimo_log": "",
        "produto_atual": "",
        "produtos_coletados": [],
        "virais_coletados": [],
    }


# ── Download de video ─────────────────────────────────────────────────────────

async def _baixar_video(nome_produto: str) -> str | None:
    """Busca e baixa um video curto do YouTube para o produto."""
    slug = re.sub(r"[^a-z0-9_]", "", nome_produto.lower().replace(" ", "_"))[:40]
    path = Path(f"data/videos/{slug}.mp4")

    if path.exists():
        logger.info(f"Video em cache: {path.name}")
        return str(path)

    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            [
                "yt-dlp", f"ytsearch3:{nome_produto} review shopee produto",
                "--match-filter", "duration < 60",
                "--format", "mp4/best[ext=mp4]",
                "--output", str(path),
                "--max-filesize", "50M",
                "--quiet", "--no-playlist",
            ],
            timeout=90,
            capture_output=True,
        )
        if path.exists():
            logger.info(f"Video baixado: {path.name} ({path.stat().st_size // 1024}KB)")
            return str(path)
    except Exception as e:
        logger.warning(f"Falha no download do video '{nome_produto}': {e}")
    return None


# ── Notificacao WhatsApp ──────────────────────────────────────────────────────

def _notificar(produto: dict, settings):
    try:
        phone = getattr(settings, "whatsapp_phone", None)
        if not phone:
            return
        from scheduler.notifier import notify_products_ready
        notify_products_ready([produto], phone, max_messages=1)
    except Exception as e:
        logger.debug(f"Notificacao WhatsApp ignorada: {e}")


# ── Processa 1 produto: baixa + posta + notifica ──────────────────────────────

async def _processar_produto(produto: dict, settings, idx: int, total: int, estado: dict) -> bool:
    """
    Pipeline direto para 1 produto:
      copy ja gerado -> baixa video -> posta -> notifica WhatsApp
    Retorna True se postou com sucesso.
    """
    nome = produto.get("produto", "Produto")[:60]
    estado["produto_atual"] = f"[{idx}/{total}] {nome}"
    estado["ultimo_log"] = f"Processando: {nome}"
    _salvar_estado(estado)

    logger.info(f"[{idx}/{total}] {nome}")

    # Baixa video
    video_path = await _baixar_video(nome)
    if not video_path:
        logger.warning(f"Sem video, pulando: {nome}")
        return False

    # Posta no Shopee Videos
    try:
        from scheduler.shopee_video_poster import post_shopee_video
        resultado = post_shopee_video(produto, video_path, settings)
    except Exception as e:
        logger.error(f"Erro ao postar '{nome}': {e}")
        return False

    if resultado.get("status") != "success":
        logger.error(f"Post falhou '{nome}': {resultado.get('error')}")
        return False

    logger.info(f"Postado com sucesso: {nome}")
    _notificar(produto, settings)

    # Aguarda antes do proximo (rate limit das plataformas)
    if idx < total:
        mins = DELAY_ENTRE_POSTS // 60
        logger.info(f"Aguardando {mins} min antes do proximo post...")
        estado["ultimo_log"] = f"Aguardando {mins}min (rate limit)"
        _salvar_estado(estado)
        await asyncio.sleep(DELAY_ENTRE_POSTS)

    return True


# ── Ciclo de produtos afiliados ───────────────────────────────────────────────

async def ciclo_produtos(settings, estado: dict) -> int:
    logger.info("-" * 50)
    logger.info("PRODUTOS AFILIADOS")
    logger.info("-" * 50)

    # 1. Scraping
    estado["ultimo_log"] = "Conectando ao Shopee Afiliados..."
    _salvar_estado(estado)
    try:
        from scraper.shopee_affiliate import scrape_all_products
        produtos = await scrape_all_products(settings)
    except Exception as e:
        logger.error(f"Erro no scraping: {e}")
        return 0

    if not produtos:
        logger.warning("Nenhum produto coletado.")
        return 0

    logger.info(f"{len(produtos)} produtos encontrados.")

    # 2. Ranking
    try:
        from scraper.product_ranker import rank_products
        top = rank_products(produtos, top_n=TOP_PRODUTOS)
    except Exception:
        top = produtos[:TOP_PRODUTOS]

    estado["produtos_coletados"] = [
        {"produto": p.get("produto", "")[:50], "comissao": p.get("comissao_atual", 0)}
        for p in top
    ]
    _salvar_estado(estado)

    # 3. Gera copy para todos em batch
    estado["ultimo_log"] = f"Gerando copy para {len(top)} produtos com IA..."
    _salvar_estado(estado)
    try:
        from ai.copy_generator import generate_batch
        top = generate_batch(
            top,
            settings.anthropic_api_key,
            settings.anthropic_model,
            settings.campaign_name,
            settings.social_network,
        )
    except Exception as e:
        logger.error(f"Erro ao gerar copy: {e}")
        return 0

    # 4. Baixa video + posta cada produto imediatamente, 1 a 1
    postados = 0
    for idx, produto in enumerate(top, 1):
        ok = await _processar_produto(produto, settings, idx, len(top), estado)
        if ok:
            postados += 1
            estado["produtos_postados_total"] += 1
            _salvar_estado(estado)

    logger.info(f"Produtos: {postados}/{len(top)} postados.")
    return postados


# ── Ciclo de virais ───────────────────────────────────────────────────────────

async def ciclo_viral(settings, estado: dict) -> int:
    logger.info("-" * 50)
    logger.info("VIDEOS VIRAIS")
    logger.info("-" * 50)

    estado["ultimo_log"] = "Buscando videos virais..."
    _salvar_estado(estado)

    try:
        from scraper.viral_video_scraper import scrape_viral_videos
        videos = await scrape_viral_videos(settings, max_videos=30, min_views=MIN_VIRAL_VIEWS)
    except Exception as e:
        logger.error(f"Erro ao buscar virais: {e}")
        return 0

    if not videos:
        logger.warning("Nenhum viral encontrado.")
        return 0

    try:
        from scraper.viral_video_ranker import selecionar_top_virais, marcar_repostados
        top = selecionar_top_virais(videos, TOP_VIRAIS, MIN_VIRAL_SCORE, MIN_VIRAL_VIEWS)
    except Exception:
        top = videos[:TOP_VIRAIS]

    if not top:
        logger.info("Nenhum viral novo passou nos criterios.")
        return 0

    estado["virais_coletados"] = [v.to_dict() for v in top]
    _salvar_estado(estado)

    # Baixa todos em paralelo (max 2 simultaneos)
    estado["ultimo_log"] = f"Baixando {len(top)} videos virais..."
    _salvar_estado(estado)
    try:
        from scheduler.viral_video_downloader import baixar_lote
        downloads = await baixar_lote(top, max_concurrent=2)
    except Exception as e:
        logger.error(f"Erro ao baixar virais: {e}")
        return 0

    # Reposta 1 a 1 imediatamente apos download
    from scheduler.viral_reposter import repostar_video
    repostados = []
    for idx, video in enumerate(top, 1):
        video_path = downloads.get(video.page_url or video.video_url)
        if not video_path:
            logger.warning(f"Video nao disponivel: {video.produto[:40]}")
            video.status = "falhou"
            continue

        estado["produto_atual"] = f"[{idx}/{len(top)}] Viral: {video.produto[:40]}"
        estado["ultimo_log"] = f"Repostando viral: {video.produto[:40]}"
        _salvar_estado(estado)

        try:
            resultado = await repostar_video(video, video_path, settings)
        except Exception as e:
            logger.error(f"Erro ao repostar '{video.produto[:40]}': {e}")
            continue

        if resultado.get("status") == "success":
            repostados.append(video)
            estado["virais_repostados_total"] += 1
            _salvar_estado(estado)

        if idx < len(top):
            logger.info(f"Aguardando {DELAY_ENTRE_POSTS // 60} min antes do proximo viral...")
            await asyncio.sleep(DELAY_ENTRE_POSTS)

    try:
        from scraper.viral_video_ranker import marcar_repostados
        if repostados:
            marcar_repostados(repostados)
    except Exception:
        pass

    logger.info(f"Virais: {len(repostados)}/{len(top)} repostados.")
    return len(repostados)


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(description="Shopee Affiliate Bot")
    parser.add_argument("--loop",   action="store_true", help=f"Repete a cada {CYCLE_HOURS}h")
    parser.add_argument("--virais", action="store_true", help="Apenas virais")
    parser.add_argument("--tudo",   action="store_true", help="Produtos + virais")
    args = parser.parse_args()

    modo = "tudo" if args.tudo else ("virais" if args.virais else "produtos")

    from config.settings import get_settings
    settings = get_settings()

    estado = _estado_inicial()
    estado["status"] = "rodando"
    _salvar_estado(estado)

    logger.info("=" * 50)
    logger.info("SHOPEE AFFILIATE BOT — PIPELINE DIRETO")
    logger.info(f"Modo: {modo} | Loop: {'sim' if args.loop else 'nao'}")
    logger.info(f"Delay entre posts: {DELAY_ENTRE_POSTS // 60} min")
    logger.info("=" * 50)

    ciclo_num = 0
    while True:
        ciclo_num += 1
        now = datetime.now()
        estado["ciclo_atual"] = ciclo_num
        estado["ultimo_ciclo"] = now.isoformat()
        estado["status"] = "executando"
        _salvar_estado(estado)

        logger.info(f"\nCICLO #{ciclo_num} — {now.strftime('%d/%m/%Y %H:%M')}")

        pp = vr = 0
        try:
            if modo in ("produtos", "tudo"):
                pp = await ciclo_produtos(settings, estado)
            if modo in ("virais", "tudo"):
                vr = await ciclo_viral(settings, estado)
        except KeyboardInterrupt:
            logger.info("Parado pelo usuario.")
            estado["status"] = "parado"
            _salvar_estado(estado)
            break
        except Exception as e:
            logger.error(f"Erro critico no ciclo #{ciclo_num}: {e}")
            estado["erros_total"] += 1
            _salvar_estado(estado)

        logger.info(
            f"Ciclo #{ciclo_num} OK — "
            f"Produtos total: {estado['produtos_postados_total']} | "
            f"Virais total: {estado['virais_repostados_total']}"
        )

        if not args.loop:
            estado["status"] = "concluido"
            _salvar_estado(estado)
            break

        proximo = now + timedelta(hours=CYCLE_HOURS)
        estado["status"] = "aguardando"
        estado["proximo_ciclo"] = proximo.isoformat()
        estado["ultimo_log"] = f"Proximo ciclo: {proximo.strftime('%H:%M')}"
        _salvar_estado(estado)
        logger.info(f"Proximo ciclo: {proximo.strftime('%d/%m/%Y %H:%M')}")
        await asyncio.sleep(CYCLE_HOURS * 3600)


if __name__ == "__main__":
    asyncio.run(main())
