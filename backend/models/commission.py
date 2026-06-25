import uuid
from datetime import datetime

from sqlalchemy import String, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base, utcnow


class Commission(Base):
    __tablename__ = "commissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id: Mapped[str] = mapped_column(String(36), ForeignKey("campaigns.id"), nullable=False)

    order_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    sale_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    commission_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    platform_fee: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending|confirmed|paid|cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    campaign = relationship("Campaign", back_populates="commissions")
