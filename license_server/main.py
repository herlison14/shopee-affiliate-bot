"""
Servidor de licenças — FastAPI

Endpoints:
  POST /webhook/mercadopago  — recebe notificação de pagamento aprovado
  POST /license/validate     — .exe valida a licença (online check)
  POST /license/activate     — .exe registra HWID na 1ª ativação
  GET  /license/public-key   — retorna chave pública para embutir no .exe
  GET  /health               — healthcheck
"""
import hashlib
import hmac
import logging
import os
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import settings
from database import License, get_db, init_db
from email_sender import send_license_email
from license_manager import (
    create_license_token,
    decode_license_token,
    generate_license_key,
    get_public_key_pem,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="License Server", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()
    logger.info("Banco de dados inicializado.")


# ── Modelos de request/response ───────────────────────────────────────────────

class ValidateRequest(BaseModel):
    license_key: str
    hwid: str | None = None


class ActivateRequest(BaseModel):
    license_key: str
    hwid: str


class ValidateResponse(BaseModel):
    valid: bool
    message: str
    expires_at: str | None = None
    days_remaining: int | None = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _verify_mp_signature(request_id: str, payment_id: str, ts: str, signature: str) -> bool:
    """Valida assinatura do webhook do Mercado Pago (x-signature header)."""
    manifest = f"id:{payment_id};request-id:{request_id};ts:{ts}"
    expected = hmac.new(
        settings.MP_WEBHOOK_SECRET.encode(),
        manifest.encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


async def _get_payment_info(payment_id: str) -> dict:
    """Consulta detalhes do pagamento na API do Mercado Pago."""
    url = f"https://api.mercadopago.com/v1/payments/{payment_id}"
    headers = {"Authorization": f"Bearer {settings.MP_ACCESS_TOKEN}"}
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()


def _issue_license(order_id: str, customer_email: str, db: Session) -> License:
    """Gera e persiste uma nova licença."""
    license_key = generate_license_key()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.LICENSE_DURATION_DAYS)

    token = create_license_token(
        license_key=license_key,
        customer_email=customer_email,
        order_id=order_id,
        expires_at=expires_at,
    )

    lic = License(
        license_key=license_key,
        order_id=order_id,
        customer_email=customer_email,
        token=token,
        expires_at=expires_at,
    )
    db.add(lic)
    db.commit()
    db.refresh(lic)
    return lic


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.get("/license/public-key", response_class=PlainTextResponse)
def public_key():
    """Retorna a chave pública RSA em formato PEM."""
    return get_public_key_pem()


@app.post("/webhook/mercadopago")
async def webhook_mercadopago(
    request: Request,
    db: Session = Depends(get_db),
    x_signature: str = Header(None),
    x_request_id: str = Header(None),
):
    """
    Recebe notificação do Mercado Pago quando pagamento é aprovado.
    Gera licença e envia por email automaticamente.
    """
    body = await request.json()
    logger.info(f"Webhook recebido: {body}")

    # Só processa pagamentos (ignora outros eventos)
    if body.get("type") != "payment":
        return {"status": "ignored"}

    payment_id = str(body.get("data", {}).get("id", ""))
    if not payment_id:
        raise HTTPException(400, "payment_id ausente")

    # ── Valida assinatura ───────────────────────────────────────────────────
    if x_signature and x_request_id:
        try:
            parts = dict(p.split("=", 1) for p in x_signature.split(","))
            ts = parts.get("ts", "")
            sig = parts.get("v1", "")
            if not _verify_mp_signature(x_request_id, payment_id, ts, sig):
                logger.warning("Assinatura do webhook inválida.")
                raise HTTPException(401, "Assinatura inválida")
        except Exception as e:
            logger.warning(f"Erro na validação de assinatura: {e}")

    # ── Consulta pagamento ──────────────────────────────────────────────────
    try:
        payment = await _get_payment_info(payment_id)
    except Exception as e:
        logger.error(f"Erro ao consultar pagamento {payment_id}: {e}")
        raise HTTPException(502, "Erro ao consultar Mercado Pago")

    status = payment.get("status")
    if status != "approved":
        logger.info(f"Pagamento {payment_id} com status '{status}' — ignorado.")
        return {"status": "ignored", "payment_status": status}

    customer_email = payment.get("payer", {}).get("email", "")
    if not customer_email:
        logger.error(f"Email do pagador não encontrado no pagamento {payment_id}")
        raise HTTPException(422, "Email do pagador não encontrado")

    order_id = str(payment.get("order", {}).get("id") or payment_id)

    # ── Idempotência: evita emitir licença duplicada ─────────────────────────
    existing = db.query(License).filter(License.order_id == order_id).first()
    if existing:
        logger.info(f"Licença já emitida para order_id={order_id}")
        return {"status": "already_issued", "license_key": existing.license_key}

    # ── Emite licença ────────────────────────────────────────────────────────
    lic = _issue_license(order_id, customer_email, db)
    logger.info(f"Licença emitida: {lic.license_key} → {customer_email}")

    # ── Envia email ──────────────────────────────────────────────────────────
    send_license_email(customer_email, lic.license_key, lic.expires_at)

    return {"status": "ok", "license_key": lic.license_key}


@app.post("/license/validate", response_model=ValidateResponse)
def validate_license(req: ValidateRequest, db: Session = Depends(get_db)):
    """
    Chamado pelo .exe ao iniciar para validar a licença online.
    Retorna validade, expiração e dias restantes.
    """
    lic = db.query(License).filter(License.license_key == req.license_key).first()

    if not lic:
        return ValidateResponse(valid=False, message="Licença não encontrada.")

    if lic.status != "active":
        return ValidateResponse(valid=False, message=f"Licença {lic.status}.")

    now = datetime.now(timezone.utc)
    expires_at = lic.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if now > expires_at:
        lic.status = "expired"
        db.commit()
        return ValidateResponse(valid=False, message="Licença expirada.")

    # Verifica HWID se já foi registrado
    if lic.hwid and req.hwid and lic.hwid != req.hwid:
        return ValidateResponse(
            valid=False,
            message="Licença vinculada a outro computador. Entre em contato com o suporte."
        )

    lic.last_check = now
    db.commit()

    days_remaining = (expires_at - now).days
    return ValidateResponse(
        valid=True,
        message="Licença válida.",
        expires_at=expires_at.strftime("%d/%m/%Y"),
        days_remaining=days_remaining,
    )


@app.post("/license/activate")
def activate_license(req: ActivateRequest, db: Session = Depends(get_db)):
    """
    Registra o HWID na 1ª ativação (vincula licença ao computador).
    """
    lic = db.query(License).filter(License.license_key == req.license_key).first()

    if not lic:
        raise HTTPException(404, "Licença não encontrada.")
    if lic.status != "active":
        raise HTTPException(403, f"Licença {lic.status}.")

    now = datetime.now(timezone.utc)
    expires_at = lic.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if now > expires_at:
        raise HTTPException(403, "Licença expirada.")

    if lic.hwid:
        if lic.hwid != req.hwid:
            raise HTTPException(
                403,
                "Licença já vinculada a outro computador. Entre em contato com o suporte."
            )
        return {"status": "already_activated", "message": "Licença já ativada neste computador."}

    lic.hwid = req.hwid
    lic.activated_at = now
    lic.last_check = now
    db.commit()

    logger.info(f"Licença {req.license_key} ativada — HWID: {req.hwid[:12]}...")
    return {"status": "activated", "message": "Licença ativada com sucesso!"}


# ── Pagamento PIX via Mercado Pago ────────────────────────────────────────────

class CreatePaymentRequest(BaseModel):
    email: str


class CreatePaymentResponse(BaseModel):
    preference_id: str
    init_point: str   # URL do Checkout Pro MP (produção)


@app.post("/payment/create", response_model=CreatePaymentResponse)
async def create_payment(req: CreatePaymentRequest):
    """
    Cria uma preferência de pagamento no Mercado Pago Checkout Pro.
    Retorna o link de checkout onde o cliente paga via PIX.
    """
    url = "https://api.mercadopago.com/checkout/preferences"
    headers = {
        "Authorization": f"Bearer {settings.MP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "items": [{
            "title": settings.PRODUCT_NAME,
            "quantity": 1,
            "unit_price": settings.PRODUCT_PRICE,
            "currency_id": "BRL",
        }],
        "payer": {"email": req.email},
        "payment_methods": {
            "excluded_payment_types": [
                {"id": "credit_card"},
                {"id": "debit_card"},
                {"id": "ticket"},
            ]
        },
        "notification_url": f"{settings.SERVER_URL}/webhook/mercadopago",
        "external_reference": req.email,
    }
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(url, json=payload, headers=headers, timeout=15)
            resp.raise_for_status()
        except Exception as e:
            logger.error(f"Erro ao criar preferência MP: {e}")
            raise HTTPException(502, "Erro ao criar pagamento no Mercado Pago")

    data = resp.json()
    return CreatePaymentResponse(
        preference_id=data["id"],
        init_point=data["init_point"],
    )


# ── Entry point para Railway / Render ─────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    from config import settings
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, workers=1)
