"""Add loan_payment to transaction_type enum.

Revision ID: 0005
Revises: 0004
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE must run outside transaction or via autocommit block
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE transaction_type ADD VALUE IF NOT EXISTS 'loan_payment'")


def downgrade() -> None:
    # Check if any loan_payment transactions exist before refusing
    conn = op.get_bind()
    count = conn.execute(
        sa.text("SELECT count(*) FROM transactions WHERE type = 'loan_payment'")
    ).scalar()
    if count and count > 0:
        raise RuntimeError("Cannot downgrade: loan_payment transactions exist")
    # In PostgreSQL, enum values cannot be removed without recreating the type
    pass
