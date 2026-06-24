"""add mcp_token to users

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-24

"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("mcp_token", sa.String(64), nullable=True))
    op.create_index("ix_users_mcp_token", "users", ["mcp_token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_mcp_token", table_name="users")
    op.drop_column("users", "mcp_token")
