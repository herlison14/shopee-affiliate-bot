"""Busca um video relevante para um produto, com checagem real de relevancia
antes de baixar -- o bot antigo baixava o PRIMEIRO resultado de busca sem checar
nada, o que podia colocar um video completamente sem relacao com o produto.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

STOPWORDS = {
    "de", "da", "do", "das", "dos", "com", "para", "por", "em", "no", "na",
    "e", "ou", "a", "o", "as", "os", "um", "uma", "uns", "umas", "kit",
}

# Abaixo disso, consideramos que o video nao tem relacao suficiente com o produto.
MIN_RELEVANCE_SCORE = 0.34


def _tokenizar(texto: str) -> set[str]:
    palavras = re.findall(r"[a-zA-Z0-9À-ÿ]+", texto.lower())
    return {p for p in palavras if len(p) > 2 and p not in STOPWORDS}


def pontuar_relevancia(nome_produto: str, titulo_video: str) -> float:
    """Retorna a fracao de palavras significativas do nome do produto que
    aparecem no titulo do video candidato (0.0 a 1.0)."""
    palavras_produto = _tokenizar(nome_produto)
    if not palavras_produto:
        return 0.0
    palavras_video = _tokenizar(titulo_video)
    intersecao = palavras_produto & palavras_video
    return len(intersecao) / len(palavras_produto)


def buscar_candidatos(nome_produto: str, max_candidatos: int = 5) -> list[dict]:
    """Busca metadados de candidatos no YouTube SEM baixar nada ainda."""
    termos = " ".join(nome_produto.split()[:5])
    query = f"ytsearch{max_candidatos}:{termos} shopee"

    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--no-playlist",
        "--dump-json",
        "--skip-download",
        "--quiet",
        query,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return []

    candidatos = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            info = json.loads(line)
        except json.JSONDecodeError:
            continue
        candidatos.append(
            {
                "id": info.get("id"),
                "url": info.get("webpage_url") or f"https://www.youtube.com/watch?v={info.get('id')}",
                "titulo": info.get("title", ""),
                "duracao_s": info.get("duration"),
            }
        )
    return candidatos


def escolher_melhor_candidato(nome_produto: str, candidatos: list[dict]) -> tuple[dict | None, float]:
    """Retorna (candidato, score) do candidato mais relevante, ou (None, 0.0)
    se nenhum atingir o limiar minimo."""
    melhor = None
    melhor_score = 0.0
    for candidato in candidatos:
        score = pontuar_relevancia(nome_produto, candidato["titulo"])
        if score > melhor_score:
            melhor, melhor_score = candidato, score

    if melhor and melhor_score >= MIN_RELEVANCE_SCORE:
        return melhor, melhor_score
    return None, melhor_score


def baixar_video(candidato: dict, destino_dir: str = "data/videos") -> str | None:
    """Baixa um candidato especifico (ja escolhido) pelo ID/URL exato."""
    destino_path = Path(destino_dir)
    destino_path.mkdir(parents=True, exist_ok=True)
    safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", candidato["id"] or "video")
    output_template = str(destino_path / f"{safe_id}.%(ext)s")

    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--no-playlist",
        "--format", "18/best[ext=mp4][filesize<50M]/best[filesize<50M]",
        "--output", output_template,
        "--quiet",
        candidato["url"],
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        return None

    for ext in [".mp4", ".webm", ".mkv", ".mov", ".avi"]:
        candidate_path = destino_path / f"{safe_id}{ext}"
        if candidate_path.exists() and candidate_path.stat().st_size > 10_000:
            return str(candidate_path)
    return None


def buscar_e_baixar_video_relevante(nome_produto: str) -> dict:
    """Fluxo completo: busca candidatos, escolhe o mais relevante, baixa.

    Retorna sempre um dict com 'video_path' (ou None) e 'motivo' explicando
    a decisao -- nunca baixa um video sem relacao minima com o produto.
    """
    candidatos = buscar_candidatos(nome_produto)
    if not candidatos:
        return {"video_path": None, "motivo": "nenhum candidato de video encontrado na busca"}

    melhor, score = escolher_melhor_candidato(nome_produto, candidatos)
    if not melhor:
        return {
            "video_path": None,
            "motivo": f"nenhum candidato atingiu relevancia minima (melhor score: {score:.2f})",
        }

    video_path = baixar_video(melhor)
    if not video_path:
        return {"video_path": None, "motivo": f"candidato relevante ('{melhor['titulo']}') falhou ao baixar"}

    return {
        "video_path": video_path,
        "motivo": f"baixado '{melhor['titulo']}' (score {score:.2f})",
        "video_titulo": melhor["titulo"],
        "video_score": score,
    }
