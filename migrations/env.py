"""Alembic environment configuration.

This file is run when you execute alembic commands.
Key customizations:
1. Import our models so autogenerate can detect them
2. Use database URL from our settings (not alembic.ini)
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Import our config and models
from src.config import get_settings
from src.models import Base  # This imports all models via __init__.py

# Alembic Config object
config = context.config

# Override the sqlalchemy.url from alembic.ini with our settings
config.set_main_option("sqlalchemy.url", get_settings().db_url)

# Setup Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Point to our models' metadata for autogenerate support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This generates SQL without connecting to the database.
    Useful for generating migration scripts to run manually.
    """
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
    """Run migrations in 'online' mode.

    This connects to the database and applies migrations directly.
    """
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
