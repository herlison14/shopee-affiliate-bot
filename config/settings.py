import os
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

# Resolve .env relative to the project root (one level up from config/)
_PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(dotenv_path=_PROJECT_ROOT / ".env", override=True)


def _require(key: str) -> str:
    val = os.getenv(key, "").strip()
    if not val:
        raise EnvironmentError(f"Variável de ambiente obrigatória não definida: {key}")
    return val


def _optional(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


@dataclass(frozen=True)
class Settings:
    # Anthropic
    anthropic_api_key: str
    anthropic_model: str

    # Shopee
    shopee_email: str
    shopee_password: str
    shopee_affiliate_url: str

    # TikTok
    tiktok_access_token: str
    tiktok_refresh_token: str
    tiktok_open_id: str

    # Campaign
    campaign_name: str
    social_network: str
    post_times: list

    # Pipeline
    max_products: int
    min_commission_pct: float
    headless: bool

    # Notificações
    whatsapp_phone: str = ""

    # SubID keys (fixed by Shopee spec)
    SUBID_PRODUCT_KEY: str = "nome_do_produto"
    SUBID_SOCIAL_KEY: str = "rede_social"
    SUBID_CAMPAIGN_KEY: str = "campanha_atual"

    # TikTok API
    TIKTOK_API_BASE: str = "https://open.tiktokapis.com/v2"

    # Excel columns (ordered)
    EXCEL_COLUMNS: tuple = (
        "produto",
        "link_original",
        "link_afiliado",
        "comissao_novo",
        "comissao_atual",
        "overlay",
        "legenda",
        "hashtags",
        "estrategia",
        "status_agendamento",
        "data_publicacao",
    )

    # File paths
    EXCEL_PATH: str = "data/output.xlsx"
    SESSION_PATH: str = "data/.shopee_session.json"
    LOG_PATH: str = "logs/affiliate_bot.log"
    SCREENSHOTS_DIR: str = "logs/screenshots"


def get_settings() -> Settings:
    post_times_raw = _optional("POST_TIMES", "09:00,13:00,20:00")
    post_times = [t.strip() for t in post_times_raw.split(",") if t.strip()]

    return Settings(
        anthropic_api_key=_require("ANTHROPIC_API_KEY"),
        anthropic_model=_optional("ANTHROPIC_MODEL", "claude-opus-4-6"),
        shopee_email=_require("SHOPEE_EMAIL"),
        shopee_password=_require("SHOPEE_PASSWORD"),
        shopee_affiliate_url=_optional(
            "SHOPEE_AFFILIATE_URL", "https://affiliate.shopee.com.br"
        ),
        tiktok_access_token=_optional("TIKTOK_ACCESS_TOKEN"),
        tiktok_refresh_token=_optional("TIKTOK_REFRESH_TOKEN"),
        tiktok_open_id=_optional("TIKTOK_OPEN_ID"),
        campaign_name=_optional("CAMPAIGN_NAME", "campanha_2026"),
        social_network=_optional("SOCIAL_NETWORK", "tiktok"),
        post_times=post_times,
        max_products=int(_optional("MAX_PRODUCTS_PER_RUN", "100")),
        min_commission_pct=float(_optional("MIN_COMMISSION_PCT", "5.0")),
        headless=_optional("HEADLESS", "true").lower() != "false",
        whatsapp_phone=_optional("WHATSAPP_PHONE", ""),
    )


# Module-level singleton — import this everywhere
try:
    settings = get_settings()
except EnvironmentError:
    # Allow import without .env (e.g. dashboard read-only mode)
    settings = None
