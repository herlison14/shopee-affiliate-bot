"""Integracao com o Instagram via Graph API (Content Publishing).

Fluxo oficial de 2 passos (feed de foto):
1. POST /{ig_user_id}/media       -> cria o container (image_url + caption) -> creation_id
2. POST /{ig_user_id}/media_publish (creation_id) -> publica -> media_id

Usa graph.facebook.com com o Instagram Business Account ID vinculado a uma
Pagina do Facebook. Nao ha automacao de navegador -- so a API oficial.
"""

import httpx

from config import settings
from models.user import User


class InstagramError(Exception):
    """Erro do fluxo de publicacao no Instagram (mensagem util pro usuario)."""


def _base() -> str:
    return settings.INSTAGRAM_GRAPH_API_BASE.rstrip("/")


def build_caption(caption: str | None, hashtags: str | None) -> str:
    """Junta legenda + hashtags e respeita o limite de 2200 chars do Instagram."""
    full = f"{caption or ''}\n\n{hashtags or ''}".strip()
    if len(full) > 2200:
        full = full[:2197] + "..."
    return full


async def get_account_info(user: User) -> dict:
    """Busca id/username da conta -- serve pra validar o token na conexao."""
    if not user.instagram_access_token or not user.instagram_user_id:
        raise InstagramError("Conta Instagram nao conectada.")
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{_base()}/{user.instagram_user_id}",
            params={"fields": "id,username", "access_token": user.instagram_access_token},
        )
    if resp.status_code != 200:
        msg = resp.json().get("error", {}).get("message", "token invalido")
        raise InstagramError(f"Nao foi possivel validar a conta: {msg}")
    return resp.json()


async def publish_photo(user: User, image_url: str, caption: str) -> dict:
    """Publica uma foto no feed. Retorna {media_id, posted_url}. Levanta InstagramError."""
    if not user.instagram_access_token or not user.instagram_user_id:
        raise InstagramError("Conta Instagram nao conectada. Conecte a conta primeiro.")
    if not image_url:
        raise InstagramError("Imagem obrigatoria: adicione uma image_url a campanha.")

    token = user.instagram_access_token
    ig_id = user.instagram_user_id

    async with httpx.AsyncClient(timeout=30) as client:
        # Passo 1: cria o container de midia
        create = await client.post(
            f"{_base()}/{ig_id}/media",
            data={"image_url": image_url, "caption": caption, "access_token": token},
        )
        if create.status_code not in (200, 201):
            msg = create.json().get("error", {}).get("message", "erro ao criar midia")
            raise InstagramError(f"Falha ao criar a midia: {msg}")
        creation_id = create.json().get("id")
        if not creation_id:
            raise InstagramError("Resposta invalida ao criar a midia (sem id).")

        # Passo 2: publica o container
        publish = await client.post(
            f"{_base()}/{ig_id}/media_publish",
            data={"creation_id": creation_id, "access_token": token},
        )
        if publish.status_code not in (200, 201):
            msg = publish.json().get("error", {}).get("message", "erro ao publicar")
            raise InstagramError(f"Falha ao publicar: {msg}")
        media_id = publish.json().get("id")
        if not media_id:
            raise InstagramError("Resposta invalida ao publicar (sem media id).")

    return {"media_id": media_id, "posted_url": f"https://www.instagram.com/p/{media_id}/"}
