"""add users.instagram_access_token, instagram_user_id, instagram_token_expires_at

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-02
"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

def upgrade() -> None:
      op.add_column("users", sa.Column("instagram_access_token", sa.String(512), nullable=True))
      op.add_column("users", sa.Column("instagram_user_id", sa.String(128), nullable=True))
      op.add_column("users", sa.Column("instagram_token_expires_at", sa.DateTime(), nullable=True))

def downgrade() -> None:
      op.drop_column("users", "instagram_token_expires_at")
      op.drop_column("users", "instagram_user_id")
      op.drop_column("users", "instagram_access_token")
