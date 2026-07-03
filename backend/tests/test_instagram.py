import pytest

from services import instagram_service
from services.instagram_service import InstagramError

pytestmark = pytest.mark.anyio


async def _register_and_login(client, email):
    await client.post("/api/v1/auth/register", json={"email": email, "password": "senha123456"})
    resp = await client.post("/api/v1/auth/login", data={"username": email, "password": "senha123456"})
    return resp.json()["access_token"]


async def _criar_campanha(client, headers, image_url=None):
    body = {"product_name": "Produto IG", "product_url": "https://shopee.com.br/product/1/2"}
    if image_url is not None:
        body["image_url"] = image_url
    resp = await client.post("/api/v1/campaigns", json=body, headers=headers)
    return resp.json()


def test_build_caption_trunca_no_limite_do_instagram():
    caption = instagram_service.build_caption("a" * 3000, "#x")
    assert len(caption) <= 2200
    assert caption.endswith("...")


async def test_status_sem_conta_conectada(client):
    token = await _register_and_login(client, "igstatus@example.com")
    resp = await client.get("/api/v1/instagram/status", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["connected"] is False


async def test_connect_valida_token_e_guarda(client, monkeypatch):
    async def fake_info(user):
        return {"id": user.instagram_user_id, "username": "achadinhosdobinga"}

    monkeypatch.setattr(instagram_service, "get_account_info", fake_info)
    token = await _register_and_login(client, "igconnect@example.com")
    resp = await client.post(
        "/api/v1/instagram/connect",
        json={"access_token": "tok_longo", "instagram_user_id": "178414"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"connected": True, "username": "achadinhosdobinga", "detail": None}


async def test_connect_token_invalido_da_401(client, monkeypatch):
    async def fake_info(user):
        raise InstagramError("token invalido")

    monkeypatch.setattr(instagram_service, "get_account_info", fake_info)
    token = await _register_and_login(client, "igbad@example.com")
    resp = await client.post(
        "/api/v1/instagram/connect",
        json={"access_token": "ruim", "instagram_user_id": "1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401


async def test_publish_sem_conta_conectada_da_400(client):
    token = await _register_and_login(client, "igpub1@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    camp = await _criar_campanha(client, headers, image_url="https://img/x.jpg")
    resp = await client.post(f"/api/v1/instagram/campaigns/{camp['id']}/publish", headers=headers)
    assert resp.status_code == 400
    assert "conectada" in resp.json()["detail"].lower()


async def test_publish_sem_imagem_da_400(client, monkeypatch):
    async def fake_info(user):
        return {"id": "1", "username": "u"}

    monkeypatch.setattr(instagram_service, "get_account_info", fake_info)
    token = await _register_and_login(client, "igpub2@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    await client.post(
        "/api/v1/instagram/connect",
        json={"access_token": "tok", "instagram_user_id": "1"},
        headers=headers,
    )
    camp = await _criar_campanha(client, headers)  # sem image_url
    resp = await client.post(f"/api/v1/instagram/campaigns/{camp['id']}/publish", headers=headers)
    assert resp.status_code == 400
    assert "imagem" in resp.json()["detail"].lower()


async def test_publish_sucesso_marca_posted(client, monkeypatch):
    async def fake_info(user):
        return {"id": "1", "username": "u"}

    async def fake_publish(user, image_url, caption):
        return {"media_id": "MEDIA1", "posted_url": "https://www.instagram.com/p/MEDIA1/"}

    monkeypatch.setattr(instagram_service, "get_account_info", fake_info)
    monkeypatch.setattr(instagram_service, "publish_photo", fake_publish)

    token = await _register_and_login(client, "igpub3@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    await client.post(
        "/api/v1/instagram/connect",
        json={"access_token": "tok", "instagram_user_id": "1"},
        headers=headers,
    )
    camp = await _criar_campanha(client, headers, image_url="https://img/x.jpg")
    resp = await client.post(f"/api/v1/instagram/campaigns/{camp['id']}/publish", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "posted"
    assert data["posted_url"] == "https://www.instagram.com/p/MEDIA1/"
