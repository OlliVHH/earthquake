"""Alembic migration environment."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import get_settings
from app.db.base import Base
from app.models.earthquake import Earthquake  # noqa: F401
from app.models.sync_state import SyncState  # noqa: F401

# --- Alembic configuration ---

# Human: Wire Alembic to app settings and SQLAlchemy model metadata for autogenerate/migrate.
# Agent: READS DATABASE_URL via get_settings; WRITES sqlalchemy.url in Alembic config; READS Base.metadata.
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)


# --- Migration runners ---

# Human: Run migrations without a live DB connection (SQL emitted to stdout).
# Agent: READS sqlalchemy.url from config; CALLS context.run_migrations in offline mode; no persistent DB writes from this process.
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


# Human: Run migrations against a live database connection (normal upgrade path).
# Agent: READS DATABASE_URL; CONNECTS via engine_from_config; WRITES schema via context.run_migrations; failure modes: connection/DDL errors abort transaction.
def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


# Human: Dispatch to offline or online migration runner based on Alembic CLI flags.
# Agent: READS context.is_offline_mode(); CALLS run_migrations_offline or run_migrations_online.
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
