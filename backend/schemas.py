from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str
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
    scheduled_for: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


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
