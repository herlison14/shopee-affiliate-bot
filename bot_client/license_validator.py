"""
Validador de licença — embutido no .exe

Fluxo na inicialização do bot:
  1. Lê chave salva em %APPDATA%/.shopee_bot_license
  2. Tenta validação ONLINE no servidor
  3. Se sem internet, valida OFFLINE via JWT (chave pública embutida)
  4. Se inválido → mostra tela de ativação
"""
import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import jwt
import requests

logger = logging.getLogger(__name__)

# ── Configurações (substituir antes de empacotar) ─────────────────────────────
SERVER_URL = "https://shopee-license-server-production.up.railway.app"
LICENSE_FILE = Path(os.environ.get("APPDATA", ".")) / ".shopee_bot_license"

# Chave pública RSA — gerada em license_server/keys/public.pem
PUBLIC_KEY_PEM = """
-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAtMnm8FiVGXIw9rkjmpDN
zMTqGr3PxRRuKoZNU4eaJnSByBQZjlQZ1lNOqzN0LqedyeGTdO1eXsbbsZZE0vAM
c3PwRzF7iuWcVVuLctdXVvRuZcbJm1SLd3SQVkw//J0pVofNjAbOVoUY+nyumqii
36f9cf/BqSN72QZHp1+noucU0bLkEKMwRPrwOmc8mpD+oRK8LtLS6z9FEDJ+AC+j
lpSy+tNUvZ+E+BxnsqMWKV+43PMIN/II8FxSUBYr0SKm6LVhdtGJoG3KyXAMZVvD
Yq4bhG8Vrtmoefa1f6+IuUsTYYjdiQhRqZjQuEwU4raqa5Ts07XHsWeBhtiAbo8G
nQIDAQAB
-----END PUBLIC KEY-----
""".strip()

# Tolerância offline: quantos dias sem internet antes de bloquear
OFFLINE_GRACE_DAYS = 7


# ── Hardware fingerprint ──────────────────────────────────────────────────────

def get_hwid() -> str:
    """
    Gera identificador único do computador.
    Combinação de UUID da máquina + nome do usuário.
    """
    try:
        machine_id = str(uuid.getnode())        # MAC address como int
        username = os.environ.get("USERNAME", "user")
        raw = f"{machine_id}-{username}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]
    except Exception:
        return hashlib.sha256(b"fallback").hexdigest()[:32]


# ── Persistência local ────────────────────────────────────────────────────────

def _save_local(data: dict):
    try:
        LICENSE_FILE.write_text(json.dumps(data))
    except Exception as e:
        logger.warning(f"Não foi possível salvar licença local: {e}")


def _load_local() -> dict | None:
    try:
        if LICENSE_FILE.exists():
            return json.loads(LICENSE_FILE.read_text())
    except Exception:
        pass
    return None


# ── Validação online ──────────────────────────────────────────────────────────

def _validate_online(license_key: str) -> dict | None:
    """
    POST /license/validate → retorna {valid, message, expires_at, days_remaining}
    Retorna None se sem conexão.
    """
    try:
        hwid = get_hwid()
        resp = requests.post(
            f"{SERVER_URL}/license/validate",
            json={"license_key": license_key, "hwid": hwid},
            timeout=8,
        )
        return resp.json()
    except requests.exceptions.ConnectionError:
        return None
    except Exception as e:
        logger.warning(f"Erro na validação online: {e}")
        return None


def _activate_online(license_key: str) -> dict:
    """Registra HWID no servidor na 1ª ativação."""
    hwid = get_hwid()
    resp = requests.post(
        f"{SERVER_URL}/license/activate",
        json={"license_key": license_key, "hwid": hwid},
        timeout=8,
    )
    return resp.json()


# ── Validação offline ─────────────────────────────────────────────────────────

def _validate_offline(license_key: str, last_online_check: str | None) -> tuple[bool, str]:
    """
    Verifica JWT local com a chave pública embutida.
    Bloqueia se OFFLINE_GRACE_DAYS sem verificar online.
    """
    local = _load_local()
    if not local or local.get("license_key") != license_key:
        return False, "Licença não encontrada localmente."

    token = local.get("token")
    if not token:
        return False, "Token local corrompido."

    # Grace period
    if last_online_check:
        try:
            last_check = datetime.fromisoformat(last_online_check)
            if last_check.tzinfo is None:
                last_check = last_check.replace(tzinfo=timezone.utc)
            delta = datetime.now(timezone.utc) - last_check
            if delta.days > OFFLINE_GRACE_DAYS:
                return False, f"Sem conexão há {delta.days} dias. Conecte à internet para continuar."
        except Exception:
            pass

    try:
        payload = jwt.decode(token, PUBLIC_KEY_PEM, algorithms=["RS256"])
        if payload.get("license_key") != license_key:
            return False, "Chave não corresponde ao token."
        return True, "Licença válida (offline)."
    except jwt.ExpiredSignatureError:
        return False, "Licença expirada."
    except jwt.InvalidTokenError as e:
        return False, f"Token inválido: {e}"


# ── Ponto de entrada principal ────────────────────────────────────────────────

def validate_license(license_key: str) -> tuple[bool, str]:
    """
    Valida a licença. Retorna (is_valid, mensagem).
    Chamada na inicialização do bot.
    """
    license_key = license_key.strip().upper()

    local = _load_local()
    last_online = local.get("last_online_check") if local else None

    # ── Tentativa online ──────────────────────────────────────────────────────
    result = _validate_online(license_key)

    if result is not None:
        if not result.get("valid"):
            return False, result.get("message", "Licença inválida.")

        # Ativação automática na 1ª vez (registra HWID)
        if not local or not local.get("activated"):
            try:
                act = _activate_online(license_key)
                logger.info(f"Ativação: {act.get('status')}")
            except Exception as e:
                logger.warning(f"Erro na ativação: {e}")

        # Salva estado local
        _save_local({
            "license_key": license_key,
            "token": local.get("token", "") if local else "",
            "expires_at": result.get("expires_at"),
            "last_online_check": datetime.now(timezone.utc).isoformat(),
            "activated": True,
        })

        days = result.get("days_remaining", 0)
        msg = f"Licença válida — {days} dias restantes."
        return True, msg

    # ── Fallback offline ──────────────────────────────────────────────────────
    logger.warning("Sem conexão — validando offline.")
    return _validate_offline(license_key, last_online)


def get_saved_license() -> str | None:
    """Retorna a chave salva localmente (para pré-preencher a tela de ativação)."""
    local = _load_local()
    return local.get("license_key") if local else None
