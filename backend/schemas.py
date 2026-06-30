from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    full_name: str | None = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: EmailStr
    full_name: str | None = None
    is_active: bool

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CampaignCreate(BaseModel):
    product_name: str
    product_url: str
    affiliate_link: str | None = None
    scheduled_for: datetime | None = None


class CampaignOut(BaseModel):
    id: str
    product_name: str
    product_url: str
    affiliate_link: str | None
    caption: str | None
    hashtags: str | None
    status: str
    status_detail: str | None = None
    posted_url: str | None = None
    scheduled_for: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


VALID_CAMPAIGN_STATUSES = {"draft", "scheduled", "posted", "failed", "needs_review"}


class CampaignStatusUpdate(BaseModel):
    status: str
    status_detail: str | None = None
    posted_url: str | None = None


class CampaignEdit(BaseModel):
    """Campos editaveis de uma campanha existente. Todos opcionais: so o que vier
    preenchido e atualizado (PATCH parcial)."""

    affiliate_link: str | None = None
    caption: str | None = None
    hashtags: str | None = None


class CommissionWebhook(BaseModel):
    campaign_id: str
    order_id: str
    sale_amount: float


class AgentActionOut(BaseModel):
    id: str
    campaign_id: str | None
    action_type: str
    description: str
    created_at: datetime

    class Config:
        from_attributes = True


class AgentSettingsOut(BaseModel):
    agent_enabled: bool


class AgentSettingsUpdate(BaseModel):
    agent_enabled: bool


class StorefrontSettingsOut(BaseModel):
    storefront_name: str
    storefront_bio: str | None = None
    storefront_url: str


class StorefrontSettingsUpdate(BaseModel):
    storefront_name: str = Field(min_length=1, max_length=255)
    storefront_bio: str | None = Field(default=None, max_length=500)


class StorefrontCampaignOut(BaseModel):
    product_name: str
    affiliate_link: str
    featured: bool


class StorefrontOut(BaseModel):
    storefront_name: str
    storefront_bio: str | None
    campaigns: list[StorefrontCampaignOut]
