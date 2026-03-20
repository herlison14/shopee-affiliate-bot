"""
Geração e validação de licenças JWT (RS256)

Fluxo:
  - Servidor usa PRIVATE KEY para assinar  → nunca exposta no .exe
  - .exe usa PUBLIC KEY para verificar     → pode ser embutida no binário
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt

from config import settings


# ── Chaves RSA ────────────────────────────────────────────────────────────────
# Prioridade: variável de ambiente → arquivo local (dev)

def _private_key() -> str:
    if settings.JWT_PRIVATE_KEY:
        # Env var: \n literal vira quebra de linha real
        return settings.JWT_PRIVATE_KEY.replace("\\n", "\n")
    p = Path(settings.JWT_PRIVATE_KEY_PATH)
    if not p.exists():
        raise FileNotFoundError(
            f"Chave privada não encontrada: {p}\n"
            "Execute: python generate_keys.py  (dev)  ou  defina JWT_PRIVATE_KEY (produção)"
        )
    return p.read_text()


def _public_key() -> str:
    if settings.JWT_PUBLIC_KEY:
        return settings.JWT_PUBLIC_KEY.replace("\\n", "\n")
    p = Path(settings.JWT_PUBLIC_KEY_PATH)
    if not p.exists():
        raise FileNotFoundError(
            f"Chave pública não encontrada: {p}\n"
            "Execute: python generate_keys.py  (dev)  ou  defina JWT_PUBLIC_KEY (produção)"
        )
    return p.read_text()


# ── Geração de chave de licença ───────────────────────────────────────────────

def generate_license_key() -> str:
    """Gera chave no formato: SHOPEE-XXXX-XXXX-XXXX-XXXX"""
    alphabet = string.ascii_uppercase + string.digits
    groups = [
        "".join(secrets.choice(alphabet) for _ in range(4))
        for _ in range(4)
    ]
    return "SHOPEE-" + "-".join(groups)


# ── JWT ───────────────────────────────────────────────────────────────────────

def create_license_token(
    license_key: str,
    customer_email: str,
    order_id: str,
    expires_at: datetime,
    hwid: str | None = None,
) -> str:
    """Assina o JWT com a chave privada RSA."""
    payload = {
        "sub": customer_email,
        "license_key": license_key,
        "order_id": order_id,
        "hwid": hwid,
        "iat": datetime.now(timezone.utc),
        "exp": expires_at,
        "product": settings.PRODUCT_NAME,
    }
    return jwt.encode(payload, _private_key(), algorithm="RS256")


def decode_license_token(token: str) -> dict:
    """Decodifica e verifica o JWT (expira automaticamente)."""
    return jwt.decode(token, _public_key(), algorithms=["RS256"])


def get_public_key_pem() -> str:
    """Retorna a chave pública para embutir no .exe."""
    return _public_key()
