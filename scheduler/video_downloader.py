"""
Video Downloader — Baixa vídeos de produtos automaticamente para data/videos/

Fontes suportadas:
  1. URL direta (mp4, mov, avi, webm)
  2. YouTube Shorts via yt-dlp
  3. TikTok via yt-dlp
  4. Shopee próprio (thumbnail animada / vídeo de produto)

Os vídeos são salvos em data/videos/ com nome baseado no produto,
prontos para uso pelo shopee_video_poster.py.
"""

import asyncio
import logging
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

VIDEOS_DIR = Path("data/videos")
MAX_VIDEO_MB = 50  # Limite Shopee
SUPPORTED_EXTS = {".mp4", ".mov", ".avi", ".webm", ".mkv"}

# Extensões de vídeo que podem vir de URL direta
DIRECT_VIDEO_EXTS = {".mp4", ".mov", ".avi", ".webm", ".mkv", ".m4v"}


# ── Utilitários ────────────────────────────────────────────────────────────────

def _sanitize_filename(name: str) -> str:
    """Converte nome do produto em nome de arquivo seguro."""
    name = re.sub(r"[^\w\s-]", "", name, flags=re.UNICODE)
    name = re.sub(r"\s+", "_", name.strip())
    return name[:60].lower()


def _videos_dir() -> Path:
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    return VIDEOS_DIR


def _already_downloaded(product_name: str) -> Path | None:
    """Verifica se já existe vídeo para este produto."""
    safe = _sanitize_filename(product_name)
    vdir = _videos_dir()
    for ext in SUPPORTED_EXTS:
        path = vdir / f"{safe}{ext}"
        if path.exists():
            return path
    return None


def _check_ytdlp() -> bool:
    """Verifica se yt-dlp está instalado."""
    try:
        subprocess.run(
            [sys.executable, "-m", "yt_dlp", "--version"],
            capture_output=True, timeout=10
        )
        return True
    except Exception:
        return False


def _install_ytdlp():
    """Instala yt-dlp automaticamente."""
    logger.info("Instalando yt-dlp...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "yt-dlp", "-q"],
        capture_output=True
    )


# ── Download via URL direta ────────────────────────────────────────────────────

def download_direct_url(url: str, output_path: Path) -> bool:
    """Baixa vídeo de URL direta (mp4, etc.)."""
    try:
        parsed = urlparse(url)
        ext = Path(parsed.path).suffix.lower()
        if ext not in DIRECT_VIDEO_EXTS:
            return False

        logger.info(f"Baixando vídeo direto: {url[:80]}")
        with httpx.stream("GET", url, follow_redirects=True, timeout=120) as r:
            if r.status_code != 200:
                return False
            total = 0
            with open(output_path, "wb") as f:
                for chunk in r.iter_bytes(chunk_size=1024 * 256):
                    f.write(chunk)
                    total += len(chunk)
                    if total > MAX_VIDEO_MB * 1024 * 1024:
                        logger.warning(f"Vídeo excede {MAX_VIDEO_MB}MB — abortando")
                        output_path.unlink(missing_ok=True)
                        return False
        logger.info(f"Download direto concluído: {output_path.name} ({total/1024/1024:.1f}MB)")
        return True
    except Exception as e:
        logger.error(f"Erro no download direto: {e}")
        return False


# ── Download via yt-dlp (YouTube Shorts / TikTok) ─────────────────────────────

def download_ytdlp(url: str, output_path: Path) -> bool:
    """Baixa vídeo via yt-dlp (YouTube, TikTok, Instagram Reels, etc.)."""
    if not _check_ytdlp():
        _install_ytdlp()

    try:
        output_template = str(output_path.with_suffix("")) + ".%(ext)s"
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "--no-playlist",
            "--format", "best[ext=mp4][filesize<50M]/best[filesize<50M]",
            "--output", output_template,
            "--no-warnings",
            "--quiet",
            url,
        ]
        logger.info(f"yt-dlp: baixando {url[:80]}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)

        # Verifica se arquivo foi criado
        mp4_path = output_path.with_suffix(".mp4")
        if mp4_path.exists() and mp4_path.stat().st_size > 10_000:
            if mp4_path != output_path:
                mp4_path.rename(output_path)
            logger.info(f"yt-dlp OK: {output_path.name} ({output_path.stat().st_size/1024/1024:.1f}MB)")
            return True

        logger.error(f"yt-dlp falhou: {result.stderr[:300]}")
        return False
    except subprocess.TimeoutExpired:
        logger.error("yt-dlp timeout (3min)")
        return False
    except Exception as e:
        logger.error(f"Erro yt-dlp: {e}")
        return False


# ── Detector de fonte ──────────────────────────────────────────────────────────

def _detect_source(url: str) -> str:
    """Detecta o tipo de fonte pelo URL."""
    if not url:
        return "none"
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    path_ext = Path(parsed.path).suffix.lower()

    if path_ext in DIRECT_VIDEO_EXTS:
        return "direct"
    if "youtube.com" in domain or "youtu.be" in domain:
        return "ytdlp"
    if "tiktok.com" in domain:
        return "ytdlp"
    if "instagram.com" in domain:
        return "ytdlp"
    if "shopee.com" in domain:
        return "shopee"
    return "none"


# ── Download para produto ──────────────────────────────────────────────────────

def download_video_for_product(product: dict, video_url: str = "") -> str | None:
    """
    Baixa vídeo para um produto e salva em data/videos/.

    Args:
        product: dict com 'produto', 'link_original', etc.
        video_url: URL do vídeo a baixar (YouTube, TikTok, MP4 direto, etc.)

    Returns:
        Caminho do arquivo baixado, ou None se falhou.
    """
    name = product.get("produto", "produto")
    safe_name = _sanitize_filename(name)
    vdir = _videos_dir()
    output_path = vdir / f"{safe_name}.mp4"

    # Já existe?
    existing = _already_downloaded(name)
    if existing:
        logger.info(f"Vídeo já existe: {existing.name}")
        return str(existing)

    if not video_url:
        logger.warning(f"Sem URL de vídeo para: {name}")
        return None

    source = _detect_source(video_url)
    logger.info(f"Baixando vídeo para '{name[:50]}' (fonte: {source})")

    if source == "direct":
        ok = download_direct_url(video_url, output_path)
    elif source == "ytdlp":
        ok = download_ytdlp(video_url, output_path)
    else:
        logger.warning(f"Fonte de vídeo não suportada: {video_url[:80]}")
        return None

    if ok and output_path.exists():
        return str(output_path)

    return None


# ── Download em lote ───────────────────────────────────────────────────────────

def download_videos_batch(products_with_urls: list[dict]) -> dict:
    """
    Baixa vídeos para múltiplos produtos.

    Args:
        products_with_urls: lista de dicts com 'product' e 'video_url'

    Returns:
        dict: {produto_nome: caminho_video_ou_None}
    """
    results = {}
    total = len(products_with_urls)

    for i, item in enumerate(products_with_urls):
        product = item.get("product", {})
        video_url = item.get("video_url", "")
        name = product.get("produto", f"produto_{i}")

        logger.info(f"[{i+1}/{total}] Baixando vídeo: {name[:50]}")
        path = download_video_for_product(product, video_url)
        results[name] = path

    downloaded = sum(1 for v in results.values() if v)
    logger.info(f"Download concluído: {downloaded}/{total} vídeos baixados")
    return results


# ── Busca automática no YouTube Shorts ────────────────────────────────────────

def search_and_download_video(product: dict) -> str | None:
    """
    Busca um vídeo no YouTube Shorts pelo nome do produto e baixa automaticamente.

    Args:
        product: dict com 'produto'

    Returns:
        Caminho do arquivo baixado, ou None se falhou.
    """
    name = product.get("produto", "")
    if not name:
        return None

    # Verifica se já existe vídeo para este produto
    existing = _already_downloaded(name)
    if existing:
        logger.info(f"Vídeo já existe: {existing.name}")
        return str(existing)

    if not _check_ytdlp():
        _install_ytdlp()

    safe_name = _sanitize_filename(name)
    vdir = _videos_dir()
    output_path = vdir / f"{safe_name}.mp4"

    # Usa as primeiras 4 palavras do nome para a busca (mais genérico = mais resultados)
    short_name = " ".join(name.split()[:4])
    query = f"{short_name} shopee"
    output_template = str(output_path.with_suffix("")) + ".%(ext)s"

    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--no-playlist",
        "--format", "18/best[ext=mp4][filesize<50M]/best[filesize<50M]",
        "--output", output_template,
        "--quiet",
        f"ytsearch1:{query}",
    ]

    try:
        logger.info(f"Buscando vídeo para: '{name[:60]}'")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        # Procura arquivo baixado em qualquer extensão suportada
        found = None
        for ext in [".mp4", ".webm", ".mkv", ".mov", ".avi"]:
            candidate = output_path.with_suffix(ext)
            if candidate.exists() and candidate.stat().st_size > 10_000:
                found = candidate
                break

        if found:
            if found != output_path:
                found.rename(output_path)
            logger.info(f"Vídeo baixado: {output_path.name} ({output_path.stat().st_size/1024/1024:.1f}MB)")
            return str(output_path)

        logger.warning(f"Nenhum vídeo encontrado para: '{name[:60]}'")
        return None
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout ao buscar vídeo para: '{name[:60]}'")
        return None
    except Exception as e:
        logger.error(f"Erro ao buscar vídeo: {e}")
        return None


def search_videos_batch(products: list) -> dict:
    """
    Busca e baixa vídeos para uma lista de produtos.

    Returns:
        dict: {produto_nome: caminho_video_ou_None}
    """
    results = {}
    total = len(products)
    for i, product in enumerate(products):
        name = product.get("produto", f"produto_{i}")
        logger.info(f"[{i+1}/{total}] Buscando vídeo: {name[:50]}")
        path = search_and_download_video(product)
        results[name] = path

    downloaded = sum(1 for v in results.values() if v)
    logger.info(f"Vídeos baixados: {downloaded}/{total}")
    return results


# ── Scanner de vídeos disponíveis ─────────────────────────────────────────────

def list_available_videos() -> list[dict]:
    """Lista todos os vídeos disponíveis em data/videos/ com metadados."""
    vdir = _videos_dir()
    videos = []

    for ext in SUPPORTED_EXTS:
        for f in vdir.glob(f"*{ext}"):
            if f.stem.endswith("_used"):
                continue
            stat = f.stat()
            videos.append({
                "arquivo": f.name,
                "caminho": str(f),
                "tamanho_mb": round(stat.st_size / 1024 / 1024, 1),
                "modificado": stat.st_mtime,
                "usado": False,
            })

    # Vídeos já usados
    for ext in SUPPORTED_EXTS:
        for f in vdir.glob(f"*_used{ext}"):
            stat = f.stat()
            videos.append({
                "arquivo": f.name,
                "caminho": str(f),
                "tamanho_mb": round(stat.st_size / 1024 / 1024, 1),
                "modificado": stat.st_mtime,
                "usado": True,
            })

    return sorted(videos, key=lambda v: v["modificado"], reverse=True)
