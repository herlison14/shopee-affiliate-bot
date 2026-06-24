from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

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

    # Payments
    STRIPE_API_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # Business
    COMMISSION_RATE: float = 0.10

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url


settings = Settings()
