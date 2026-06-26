import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base, utcnow


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)

    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    affiliate_link: Mapped[str] = mapped_column(String(1024), nullable=True)

    caption: Mapped[str] = mapped_column(Text, nullable=True)
    hashtags: Mapped[str] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(32), default="draft")  # draft|scheduled|posted|failed|needs_review
    status_detail: Mapped[str] = mapped_column(Text, nullable=True)
    posted_url: Mapped[str] = mapped_column(String(1024), nullable=True)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    owner = relationship("User", back_populates="campaigns")
    commissions = relationship("Commission", back_populates="campaign", cascade="all, delete-orphan")
