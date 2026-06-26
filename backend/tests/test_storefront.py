import pytest

pytestmark = pytest.mark.anyio


async def _register_and_login(client, email="vitrineuser@example.com"):
    await client.post("/api/v1/auth/register", json={"email": email, "password": "senha123456"})
    resp = await client.post("/api/v1/auth/login", data={"username": email, "password": "senha123456"})
    return resp.json()["access_token"]


async def test_storefront_settings_default_and_update(client):
    token = await _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/api/v1/storefront/settings", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["storefront_name"] == "Minha Vitrine"

    resp = await client.put(
        "/api/v1/storefront/settings",
        json={"storefront_name": "Achadinhos da Maria", "storefront_bio": "Curadoria de ofertas"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["storefront_name"] == "Achadinhos da Maria"
    assert body["storefront_bio"] == "Curadoria de ofertas"
    assert "/vitrine/" in body["storefront_url"]


async def test_public_storefront_only_shows_ready_campaigns(client):
    token = await _register_and_login(client, email="vitrineuser2@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    me = await client.get("/api/v1/auth/me", headers=headers)
    user_id = me.json()["id"]

    # rascunho sem link -- nao deve aparecer
    await client.post(
        "/api/v1/campaigns",
        json={"product_name": "Rascunho sem link", "product_url": "https://shopee.com.br/a"},
        headers=headers,
    )
    # com link, mas precisa promover (status fica draft por padrao -- atualizamos pra scheduled)
    resp = await client.post(
        "/api/v1/campaigns",
        json={
            "product_name": "Produto pronto",
            "product_url": "https://shopee.com.br/b",
            "affiliate_link": "https://s.shopee.com.br/abc123",
        },
        headers=headers,
    )
    campaign_id = resp.json()["id"]
    await client.patch(
        f"/api/v1/campaigns/{campaign_id}/status", json={"status": "scheduled"}, headers=headers
    )

    resp = await client.get(f"/api/v1/public/storefront/{user_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["storefront_name"] == "Minha Vitrine"
    assert len(body["campaigns"]) == 1
    assert body["campaigns"][0]["product_name"] == "Produto pronto"
    assert body["campaigns"][0]["affiliate_link"] == "https://s.shopee.com.br/abc123"
    assert body["campaigns"][0]["featured"] is False


async def test_public_storefront_404_for_unknown_user(client):
    resp = await client.get("/api/v1/public/storefront/usuario-inexistente")
    assert resp.status_code == 404
