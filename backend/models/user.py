import uuid
from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base, utcnow


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)

    storefront_name: Mapped[str] = mapped_column(String(255), nullable=True)
    storefront_bio: Mapped[str] = mapped_column(Text, nullable=True)

    shopee_access_token: Mapped[str] = mapped_column(String(512), nullable=True)
    shopee_refresh_token: Mapped[str] = mapped_column(String(512), nullable=True)
    shopee_shop_id: Mapped[str] = mapped_column(String(64), nullable=True)

    mcp_token: Mapped[str] = mapped_column(String(64), unique=True, nullable=True, index=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    agent_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    campaigns = relationship("Campaign", back_populates="owner", cascade="all, delete-orphan")
