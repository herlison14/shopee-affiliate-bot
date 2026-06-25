import pytest

pytestmark = pytest.mark.anyio


async def _register_and_login(client):
    await client.post(
        "/api/v1/auth/register", json={"email": "settingsuser@example.com", "password": "senha123456"}
    )
    resp = await client.post(
        "/api/v1/auth/login", data={"username": "settingsuser@example.com", "password": "senha123456"}
    )
    return resp.json()["access_token"]


async def test_agent_settings_default_enabled_and_toggle(client):
    token = await _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/api/v1/agent/settings", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["agent_enabled"] is True

    resp = await client.put("/api/v1/agent/settings", json={"agent_enabled": False}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["agent_enabled"] is False

    resp = await client.get("/api/v1/agent/settings", headers=headers)
    assert resp.json()["agent_enabled"] is False
