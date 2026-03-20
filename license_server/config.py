"""
Configurações do servidor de licenças — carregadas via .env ou variáveis de ambiente.

Em produção (Railway/Render), as chaves RSA são passadas como variáveis de ambiente
em formato PEM direto (com \n substituído por \\n no painel da plataforma).
"""
import base64
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Mercado Pago ──────────────────────────────────────────────────────────
    MP_ACCESS_TOKEN: str
    MP_WEBHOOK_SECRET: str

    # ── JWT (RS256) — chaves como strings (não arquivos) ─────────────────────
    # Em produção: cole o conteúdo do .pem com \n literal nas env vars da plataforma
    # Em dev local: ainda pode usar os arquivos via JWT_PRIVATE_KEY_PATH
    JWT_PRIVATE_KEY: str = ""       # Conteúdo PEM da chave privada
    JWT_PUBLIC_KEY: str = ""        # Conteúdo PEM da chave pública
    JWT_PRIVATE_KEY_PATH: str = "keys/private.pem"  # Fallback local
    JWT_PUBLIC_KEY_PATH: str = "keys/public.pem"    # Fallback local
    LICENSE_DURATION_DAYS: int = 365

    # ── Email (SMTP) ──────────────────────────────────────────────────────────
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str
    SMTP_PASS: str
    EMAIL_FROM_NAME: str = "Shopee Affiliate Bot"

    # ── Servidor ──────────────────────────────────────────────────────────────
    # Railway injeta DATABASE_URL automaticamente quando adiciona PostgreSQL
    DATABASE_URL: str = "sqlite:///./licenses.db"
    PORT: int = 8000  # Railway injeta PORT automaticamente
    SERVER_URL: str = "http://localhost:8000"
    PRODUCT_NAME: str = "Shopee Affiliate Bot"
    PRODUCT_PRICE: float = 79.90

    class Config:
        env_file = ".env"


settings = Settings()
