import hashlib
import hmac
import time

import httpx

from config import settings

SHOPEE_AUTH_BASE = "https://partner.shopeemobile.com/api/v2/shop/auth_partner"
SHOPEE_TOKEN_URL = "https://partner.shopeemobile.com/api/v2/auth/token/get"


def _sign(path: str, timestamp: int, access_token: str = "", shop_id: str = "") -> str:
    base_string = f"{settings.SHOPEE_CONSUMER_KEY}{path}{timestamp}{access_token}{shop_id}"
    return hmac.new(
        settings.SHOPEE_CONSUMER_SECRET.encode(),
        base_string.encode(),
        hashlib.sha256,
    ).hexdigest()


def build_authorization_url() -> str:
    timestamp = int(time.time())
    path = "/api/v2/shop/auth_partner"
    sign = _sign(path, timestamp)
    return (
        f"{SHOPEE_AUTH_BASE}?partner_id={settings.SHOPEE_CONSUMER_KEY}"
        f"&timestamp={timestamp}&sign={sign}&redirect={settings.SHOPEE_REDIRECT_URI}"
    )


async def exchange_code_for_token(code: str, shop_id: str) -> dict:
    timestamp = int(time.time())
    path = "/api/v2/auth/token/get"
    sign = _sign(path, timestamp)

    payload = {
        "code": code,
        "partner_id": int(settings.SHOPEE_CONSUMER_KEY) if settings.SHOPEE_CONSUMER_KEY.isdigit() else settings.SHOPEE_CONSUMER_KEY,
        "shop_id": int(shop_id) if shop_id.isdigit() else shop_id,
    }
    params = {"partner_id": settings.SHOPEE_CONSUMER_KEY, "timestamp": timestamp, "sign": sign}

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(SHOPEE_TOKEN_URL, params=params, json=payload)
        resp.raise_for_status()
        return resp.json()


async def refresh_access_token(refresh_token: str, shop_id: str) -> dict:
    timestamp = int(time.time())
    path = "/api/v2/auth/access_token/get"
    sign = _sign(path, timestamp)

    payload = {
        "refresh_token": refresh_token,
        "partner_id": settings.SHOPEE_CONSUMER_KEY,
        "shop_id": shop_id,
    }
    params = {"partner_id": settings.SHOPEE_CONSUMER_KEY, "timestamp": timestamp, "sign": sign}

    url = "https://partner.shopeemobile.com/api/v2/auth/access_token/get"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(url, params=params, json=payload)
        resp.raise_for_status()
        return resp.json()
