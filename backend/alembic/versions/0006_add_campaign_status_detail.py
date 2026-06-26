"""add campaigns.status_detail e campaigns.posted_url (status needs_review)

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-25

"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("campaigns", sa.Column("status_detail", sa.Text(), nullable=True))
    op.add_column("campaigns", sa.Column("posted_url", sa.String(1024), nullable=True))


def downgrade() -> None:
    op.drop_column("campaigns", "posted_url")
    op.drop_column("campaigns", "status_detail")
