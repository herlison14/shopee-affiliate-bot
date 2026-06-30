import pytest

pytestmark = pytest.mark.anyio


async def _register_and_login(client, email="bulkuser@example.com"):
    await client.post("/api/v1/auth/register", json={"email": email, "password": "senha123456"})
    resp = await client.post("/api/v1/auth/login", data={"username": email, "password": "senha123456"})
    return resp.json()["access_token"]


async def test_bulk_create_campaigns(client):
    token = await _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "items": [
            {"product_name": "Produto A", "product_url": "https://shopee.com.br/a"},
            {"product_name": "Produto B", "product_url": "https://shopee.com.br/b", "affiliate_link": "https://s.shopee.com.br/b"},
        ]
    }
    resp = await client.post("/api/v1/campaigns/bulk", json=payload, headers=headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["criadas"] == 2
    assert body["ignoradas_duplicadas"] == 0
    assert len(body["campaigns"]) == 2


async def test_bulk_skips_duplicates_within_batch_and_existing(client):
    token = await _register_and_login(client, email="bulkuser2@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # cria uma campanha antes
    await client.post(
        "/api/v1/campaigns",
        json={"product_name": "Ja existe", "product_url": "https://shopee.com.br/x"},
        headers=headers,
    )

    payload = {
        "items": [
            {"product_name": "Dup existente", "product_url": "https://shopee.com.br/x"},  # ja existe
            {"product_name": "Novo", "product_url": "https://shopee.com.br/y"},
            {"product_name": "Dup no lote", "product_url": "https://shopee.com.br/y"},  # dup dentro do lote
        ]
    }
    resp = await client.post("/api/v1/campaigns/bulk", json=payload, headers=headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["criadas"] == 1
    assert body["ignoradas_duplicadas"] == 2
