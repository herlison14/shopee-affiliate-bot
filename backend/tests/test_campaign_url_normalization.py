import pytest

pytestmark = pytest.mark.anyio


async def _register_and_login(client, email):
    await client.post("/api/v1/auth/register", json={"email": email, "password": "senha123456"})
    resp = await client.post("/api/v1/auth/login", data={"username": email, "password": "senha123456"})
    return resp.json()["access_token"]


async def test_campanha_com_link_de_oferta_e_sinalizada(client):
    token = await _register_and_login(client, "oferta@example.com")
    resp = await client.post(
        "/api/v1/campaigns",
        json={
            "product_name": "Produto de oferta",
            "product_url": "https://shopee.com.br/offer/product_offer/23798128210",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    # URL instavel: fica inalterada mas a campanha vem com aviso em status_detail.
    assert data["product_url"] == "https://shopee.com.br/offer/product_offer/23798128210"
    assert data["status_detail"] is not None
    assert "instável" in data["status_detail"]


async def test_campanha_com_url_canonica_e_normalizada_sem_aviso(client):
    token = await _register_and_login(client, "canonica@example.com")
    resp = await client.post(
        "/api/v1/campaigns",
        json={
            "product_name": "Beauty of Joseon",
            "product_url": "https://shopee.com.br/Beauty-of-Joseon-i.123456.789012?sp_atk=abc",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["product_url"] == "https://shopee.com.br/product/123456/789012"
    assert data["status_detail"] is None


async def test_bulk_dedup_por_url_canonica(client):
    token = await _register_and_login(client, "bulk@example.com")
    # Mesmo produto em dois formatos diferentes -> deve criar so 1 (dedup canonico).
    resp = await client.post(
        "/api/v1/campaigns/bulk",
        json={
            "items": [
                {"product_name": "A", "product_url": "https://shopee.com.br/Slug-i.111.222"},
                {"product_name": "A de novo", "product_url": "https://shopee.com.br/product/111/222"},
            ]
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["criadas"] == 1
    assert data["ignoradas_duplicadas"] == 1
