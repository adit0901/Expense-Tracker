"""Append-only audit_log.

Revision ID: 0002
Revises: 0001
"""

from __future__ import annotations

import os

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

APP_ROLE = os.environ.get("APP_DB_ROLE", "fintrack_app")


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_user_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("changed_fields", pg.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("request_id", sa.String(64), nullable=True),
        sa.Column(
            "occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_audit_log_actor_user_id", "audit_log", ["actor_user_id"])
    op.create_index("ix_audit_log_entity", "audit_log", ["entity_type", "entity_id"])
    # Append-only for the application role.
    op.execute(f'REVOKE UPDATE, DELETE, TRUNCATE ON audit_log FROM "{APP_ROLE}"')
    op.execute(f'GRANT SELECT, INSERT ON audit_log TO "{APP_ROLE}"')
    # Anonymization on account deletion runs with owner rights; the app role cannot UPDATE.
    op.execute(
        """
        CREATE FUNCTION anonymize_audit_actor(p_user_id uuid) RETURNS integer
        LANGUAGE sql SECURITY DEFINER SET search_path = public AS $$
            WITH u AS (
                UPDATE audit_log SET actor_user_id = NULL WHERE actor_user_id = p_user_id
                RETURNING 1
            )
            SELECT count(*)::integer FROM u
        $$
        """
    )
    op.execute("REVOKE ALL ON FUNCTION anonymize_audit_actor(uuid) FROM PUBLIC")
    op.execute(f'GRANT EXECUTE ON FUNCTION anonymize_audit_actor(uuid) TO "{APP_ROLE}"')


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS anonymize_audit_actor(uuid)")
    op.drop_table("audit_log")
