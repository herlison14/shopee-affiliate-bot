import pytest

pytestmark = pytest.mark.anyio


async def _mcp_call(client, mcp_token, method, params=None, request_id=1):
    payload = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        payload["params"] = params
    headers = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
    async with client.stream("POST", f"/agent/{mcp_token}/mcp", json=payload, headers=headers) as resp:
        lines = [line async for line in resp.aiter_lines() if line]
        return resp.status_code, lines


async def _register_and_get_mcp_token(client):
    await client.post(
        "/api/v1/auth/register", json={"email": "mcpuser@example.com", "password": "senha123456"}
    )
    resp = await client.post(
        "/api/v1/auth/login", data={"username": "mcpuser@example.com", "password": "senha123456"}
    )
    access_token = resp.json()["access_token"]

    resp = await client.get("/api/v1/auth/mcp-url", headers={"Authorization": f"Bearer {access_token}"})
    assert resp.status_code == 200
    mcp_url = resp.json()["mcp_url"]
    return mcp_url.split("/agent/")[1].split("/mcp")[0]


async def test_mcp_create_and_list_campaign(client):
    mcp_token = await _register_and_get_mcp_token(client)

    init_params = {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "pytest", "version": "0.1"},
    }
    status, _ = await _mcp_call(client, mcp_token, "initialize", init_params)
    assert status == 200

    status, lines = await _mcp_call(
        client,
        mcp_token,
        "tools/call",
        {"name": "criar_campanha", "arguments": {"nome_produto": "Caneca termica", "url_produto": "https://shopee.com.br/x"}},
        request_id=2,
    )
    assert status == 200
    assert any('"isError":false' in line for line in lines)

    status, lines = await _mcp_call(
        client, mcp_token, "tools/call", {"name": "listar_campanhas", "arguments": {}}, request_id=3
    )
    assert status == 200
    assert any("Caneca termica" in line for line in lines)


async def test_mcp_rejects_invalid_token(client):
    status, lines = await _mcp_call(
        client, "token-invalido", "tools/call", {"name": "listar_campanhas", "arguments": {}}
    )
    assert status == 200
    assert any('"isError":true' in line for line in lines)
    assert any("Token MCP" in line for line in lines)
