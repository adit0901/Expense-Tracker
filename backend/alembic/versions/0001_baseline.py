"""Baseline: extensions and privileges for the application role.

Revision ID: 0001
Revises:
"""

from __future__ import annotations

import os

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

APP_ROLE = os.environ.get("APP_DB_ROLE", "fintrack_app")


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(f'GRANT USAGE ON SCHEMA public TO "{APP_ROLE}"')
    # Tables created later by the owner role are usable by the app role by default.
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        f'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "{APP_ROLE}"'
    )
    op.execute(
        f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO "{APP_ROLE}"'
    )
    op.execute(f'GRANT SELECT ON TABLE alembic_version TO "{APP_ROLE}"')


def downgrade() -> None:
    op.execute(f'REVOKE SELECT ON TABLE alembic_version FROM "{APP_ROLE}"')
    op.execute(
        f'ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE USAGE, SELECT ON SEQUENCES FROM "{APP_ROLE}"'
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        f'REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM "{APP_ROLE}"'
    )
    op.execute(f'REVOKE USAGE ON SCHEMA public FROM "{APP_ROLE}"')
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
    op.execute("DROP EXTENSION IF EXISTS citext")
