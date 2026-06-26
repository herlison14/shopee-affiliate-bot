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
