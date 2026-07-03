from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    ENVIRONMENT: str = "development"  # setar "production" no Render (ativa o guard do SECRET_KEY)
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    # Webhooks
    # Por padrao o webhook de venda e fail-closed: se SHOPEE_CONSUMER_SECRET nao
    # estiver configurado, requests nao-assinados sao REJEITADOS (senao qualquer
    # um poderia forjar vendas). So habilite isto em ambiente de teste/dev.
    WEBHOOK_ALLOW_UNSIGNED: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/shopee_viral_saas"

    # Shopee OAuth
    SHOPEE_CONSUMER_KEY: str = ""
    SHOPEE_CONSUMER_SECRET: str = ""
    SHOPEE_REDIRECT_URI: str = "https://shopee-viral-api.onrender.com/api/v1/auth/callback"

    # Frontend
    FRONTEND_URL: str = "http://localhost:5173"

    # AI
    ANTHROPIC_API_KEY: str = ""

    # Instagram (Graph API - Content Publishing). Content publishing usa
    # graph.facebook.com com o IG Business Account ID vinculado a uma Pagina do FB
    # (NAO graph.instagram.com, que e a Basic Display API e nao publica).
    INSTAGRAM_APP_ID: str = ""
    INSTAGRAM_APP_SECRET: str = ""
    INSTAGRAM_GRAPH_API_BASE: str = "https://graph.facebook.com/v21.0"

    # Payments
    STRIPE_API_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # Business
    COMMISSION_RATE: float = 0.10

    # Agente autonomo (James)
    AGENT_CYCLE_HOURS: float = 6
    AGENT_ENABLED: bool = True

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url


settings = Settings()

# Fail-closed: nunca rodar em producao com a SECRET_KEY default (JWT forjavel).
# So dispara quando ENVIRONMENT=production (setado no Render); em dev/teste
# apenas avisa, sem derrubar a app.
if settings.SECRET_KEY == "change-me-in-production":
    if settings.ENVIRONMENT == "production":
        raise RuntimeError(
            "SECRET_KEY nao configurada em producao (esta com o default inseguro). "
            "Defina SECRET_KEY nas variaveis de ambiente antes de subir."
        )
    import logging

    logging.getLogger("shopeeviral").warning(
        "SECRET_KEY esta com o valor default -- OK em dev, mas NUNCA suba assim em producao."
    )
