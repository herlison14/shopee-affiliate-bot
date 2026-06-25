"""add agent_actions table (agente James)

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-25

"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_actions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("campaign_id", sa.String(36), sa.ForeignKey("campaigns.id"), nullable=True),
        sa.Column("action_type", sa.String(64), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_agent_actions_user_id", "agent_actions", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_actions_user_id", table_name="agent_actions")
    op.drop_table("agent_actions")
