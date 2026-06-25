"""commissions.order_id unique (idempotencia do webhook de vendas)

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-25

"""
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint("uq_commissions_order_id", "commissions", ["order_id"])


def downgrade() -> None:
    op.drop_constraint("uq_commissions_order_id", "commissions", type_="unique")
