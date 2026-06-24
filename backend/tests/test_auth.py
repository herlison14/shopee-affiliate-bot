import pytest

pytestmark = pytest.mark.anyio


async def test_register_and_login(client):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "teste@exemplo.com", "password": "senha123", "full_name": "Teste"},
    )
    assert resp.status_code == 201
    assert resp.json()["email"] == "teste@exemplo.com"

    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "teste@exemplo.com", "password": "senha123"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    assert token

    resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "teste@exemplo.com"


async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
