"""
Alembic environment script.

WHY `target_metadata = Base.metadata` MATTERS:
This is what powers `alembic revision --autogenerate`: Alembic
compares the CURRENT database schema against `Base.metadata` (i.e.
against your Python model definitions) and writes a migration script
containing only the diff. If `app.models` weren't imported (see the
comment in app/models/__init__.py), tables missing from that import
would look "not part of the app" to Alembic and it would generate a
migration to DROP them -- a genuinely dangerous silent-data-loss trap
if you weren't importing every model somewhere.

Autogenerate is a helpful first draft, not a guarantee -- always read
the generated migration file before running it, especially for
renames (which autogenerate sees as "drop column A, add column B" and
would happily delete the data in A).
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app import models  # noqa: F401 -- ensures every model is registered on Base.metadata
from app.core.config import settings
from app.db.base_class import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Inject the real DB URL from app settings instead of alembic.ini,
# so there's a single source of truth for the connection string.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Generates SQL scripts without a live DB connection (for DBAs to review/run manually)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """The normal path: connect to the DB and apply migrations directly."""
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
