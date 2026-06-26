import pytest

pytestmark = pytest.mark.anyio


async def _register_and_login(client, email="statususer@example.com"):
    await client.post("/api/v1/auth/register", json={"email": email, "password": "senha123456"})
    resp = await client.post("/api/v1/auth/login", data={"username": email, "password": "senha123456"})
    return resp.json()["access_token"]


async def test_update_campaign_status_to_posted_with_url(client):
    token = await _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(
        "/api/v1/campaigns",
        json={"product_name": "Produto X", "product_url": "https://shopee.com.br/x"},
        headers=headers,
    )
    campaign_id = resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/campaigns/{campaign_id}/status",
        json={"status": "posted", "posted_url": "https://shopeevideo.com.br/v/123"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "posted"
    assert body["posted_url"] == "https://shopeevideo.com.br/v/123"


async def test_update_campaign_status_rejects_invalid_status(client):
    token = await _register_and_login(client, email="statususer2@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(
        "/api/v1/campaigns",
        json={"product_name": "Produto Y", "product_url": "https://shopee.com.br/y"},
        headers=headers,
    )
    campaign_id = resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/campaigns/{campaign_id}/status",
        json={"status": "isso_nao_existe"},
        headers=headers,
    )
    assert resp.status_code == 422


async def test_list_campaigns_filtered_by_product_url(client):
    token = await _register_and_login(client, email="statususer3@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    await client.post(
        "/api/v1/campaigns",
        json={"product_name": "Produto Z", "product_url": "https://shopee.com.br/z"},
        headers=headers,
    )
    await client.post(
        "/api/v1/campaigns",
        json={"product_name": "Produto W", "product_url": "https://shopee.com.br/w"},
        headers=headers,
    )

    resp = await client.get(
        "/api/v1/campaigns", params={"product_url": "https://shopee.com.br/z"}, headers=headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["product_url"] == "https://shopee.com.br/z"
