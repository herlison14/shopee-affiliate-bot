"""add campaigns.image_url (mídia para publicação no Instagram)

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-02

"""
from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("campaigns", sa.Column("image_url", sa.String(1024), nullable=True))


def downgrade() -> None:
    op.drop_column("campaigns", "image_url")
