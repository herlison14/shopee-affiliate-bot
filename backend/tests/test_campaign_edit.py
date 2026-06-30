import pytest

pytestmark = pytest.mark.anyio


async def _register_and_login(client, email="edituser@example.com"):
    await client.post("/api/v1/auth/register", json={"email": email, "password": "senha123456"})
    resp = await client.post("/api/v1/auth/login", data={"username": email, "password": "senha123456"})
    return resp.json()["access_token"]


async def test_edit_campaign_affiliate_link(client):
    token = await _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(
        "/api/v1/campaigns",
        json={"product_name": "Produto sem link", "product_url": "https://shopee.com.br/x"},
        headers=headers,
    )
    campaign_id = resp.json()["id"]
    assert resp.json()["affiliate_link"] is None

    resp = await client.patch(
        f"/api/v1/campaigns/{campaign_id}",
        json={"affiliate_link": "https://s.shopee.com.br/abc123"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["affiliate_link"] == "https://s.shopee.com.br/abc123"


async def test_edit_campaign_partial_does_not_clear_other_fields(client):
    token = await _register_and_login(client, email="edituser2@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(
        "/api/v1/campaigns",
        json={"product_name": "Produto Y", "product_url": "https://shopee.com.br/y"},
        headers=headers,
    )
    campaign_id = resp.json()["id"]
    caption_original = resp.json()["caption"]

    # so envia affiliate_link -- caption nao pode ser apagada
    resp = await client.patch(
        f"/api/v1/campaigns/{campaign_id}",
        json={"affiliate_link": "https://s.shopee.com.br/xyz"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["caption"] == caption_original
    assert resp.json()["affiliate_link"] == "https://s.shopee.com.br/xyz"


async def test_edit_campaign_404_for_other_user(client):
    token_a = await _register_and_login(client, email="owner@example.com")
    resp = await client.post(
        "/api/v1/campaigns",
        json={"product_name": "Produto Z", "product_url": "https://shopee.com.br/z"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    campaign_id = resp.json()["id"]

    token_b = await _register_and_login(client, email="intruso@example.com")
    resp = await client.patch(
        f"/api/v1/campaigns/{campaign_id}",
        json={"affiliate_link": "https://s.shopee.com.br/hack"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 404
