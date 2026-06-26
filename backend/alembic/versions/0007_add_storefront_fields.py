"""add users.storefront_name e users.storefront_bio (vitrine publica)

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-26

"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("storefront_name", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("storefront_bio", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "storefront_bio")
    op.drop_column("users", "storefront_name")
