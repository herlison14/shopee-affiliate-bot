import hashlib
import hmac
import json

import pytest
from sqlalchemy import select

import database
from config import settings
from models.campaign import Campaign
from models.user import User
from security import hash_password

pytestmark = pytest.mark.anyio


async def _create_campaign(db) -> Campaign:
    user = User(email="webhookuser@example.com", hashed_password=hash_password("senha123456"))
    db.add(user)
    await db.commit()
    await db.refresh(user)

    campaign = Campaign(
        user_id=user.id,
        product_name="Produto teste webhook",
        product_url="https://shopee.com.br/x",
        status="scheduled",
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return campaign


async def test_webhook_without_secret_configured_accepts_any_request(client):
    async with database.AsyncSessionLocal() as db:
        campaign = await _create_campaign(db)

    payload = {"campaign_id": campaign.id, "order_id": "PED-001", "sale_amount": 100.0}
    resp = await client.post("/api/v1/webhooks/shopee/sale", json=payload)
    assert resp.status_code == 201
    assert resp.json()["status"] == "pending"


async def test_webhook_is_idempotent_on_repeated_order_id(client):
    async with database.AsyncSessionLocal() as db:
        campaign = await _create_campaign(db)

    payload = {"campaign_id": campaign.id, "order_id": "PED-002", "sale_amount": 50.0}
    first = await client.post("/api/v1/webhooks/shopee/sale", json=payload)
    second = await client.post("/api/v1/webhooks/shopee/sale", json=payload)

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["duplicate"] is True
    assert first.json()["commission_id"] == second.json()["commission_id"]


async def test_webhook_rejects_invalid_signature_when_secret_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "SHOPEE_CONSUMER_SECRET", "test-partner-key")

    async with database.AsyncSessionLocal() as db:
        campaign = await _create_campaign(db)

    payload = {"campaign_id": campaign.id, "order_id": "PED-003", "sale_amount": 75.0}
    resp = await client.post(
        "/api/v1/webhooks/shopee/sale", json=payload, headers={"Authorization": "assinatura-errada"}
    )
    assert resp.status_code == 401


async def test_webhook_accepts_valid_signature_when_secret_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "SHOPEE_CONSUMER_SECRET", "test-partner-key")

    async with database.AsyncSessionLocal() as db:
        campaign = await _create_campaign(db)

    payload = {"campaign_id": campaign.id, "order_id": "PED-004", "sale_amount": 30.0}
    body = json.dumps(payload).encode()
    url = "http://test/api/v1/webhooks/shopee/sale"
    base_string = f"{url}|{body.decode()}"
    signature = hmac.new(b"test-partner-key", base_string.encode(), hashlib.sha256).hexdigest()

    resp = await client.post(
        "/api/v1/webhooks/shopee/sale",
        content=body,
        headers={"Authorization": signature, "Content-Type": "application/json"},
    )
    assert resp.status_code == 201
