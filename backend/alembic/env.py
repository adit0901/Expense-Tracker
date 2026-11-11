"""Alembic environment. Migrations run as the schema owner role (MIGRATION_DATABASE_URL)."""

from __future__ import annotations

import os

from sqlalchemy import engine_from_config, pool

import app.models  # noqa: F401  - register all models
from alembic import context
from app.core.config import get_settings
from app.core.db import Base

config = context.config
url = os.environ.get("MIGRATION_DATABASE_URL_OVERRIDE") or get_settings().migration_database_url
config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
