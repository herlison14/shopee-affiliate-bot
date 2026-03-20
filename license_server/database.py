"""
Banco de dados — SQLite (dev local) ou PostgreSQL (Railway/Render em produção)
"""
from datetime import datetime
from sqlalchemy import create_engine, Column, String, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker

from config import settings

# Railway injeta DATABASE_URL como postgresql:// — connect_args só vale para SQLite
_is_sqlite = settings.DATABASE_URL.startswith("sqlite")
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class License(Base):
    __tablename__ = "licenses"

    license_key = Column(String, primary_key=True, index=True)
    order_id    = Column(String, unique=True, index=True)
    customer_email = Column(String, index=True)
    token       = Column(Text)           # JWT assinado
    hwid        = Column(String, nullable=True)  # hardware fingerprint (após 1ª ativação)
    status      = Column(String, default="active")  # active | suspended | expired
    issued_at   = Column(DateTime, default=datetime.utcnow)
    expires_at  = Column(DateTime)
    activated_at = Column(DateTime, nullable=True)
    last_check  = Column(DateTime, nullable=True)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
