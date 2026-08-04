import asyncio
from logging.config import fileConfig

from sqlalchemy.engine import Connection

from alembic import context

from app.infrastructure.persistence.database import (
    build_engine,
    is_sqlite,
    normalize_database_url,
)
from app.infrastructure.persistence.models import Base
from app.infrastructure.persistence.types import UtcDateTime
from app.shared.config.settings import settings


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def render_item(type_: str, obj, autogen_context) -> str | bool:
    """Evita que las migraciones importen tipos propios de la aplicacion.

    Una migracion es una foto inmutable del esquema: si renombramos o
    borramos UtcDateTime, las migraciones viejas seguirian funcionando.
    """
    if type_ == "type" and isinstance(obj, UtcDateTime):
        autogen_context.imports.add("import sqlalchemy as sa")

        return "sa.DateTime(timezone=True)"

    return False


def _context_options() -> dict:
    return {
        "target_metadata": target_metadata,
        "compare_type": True,
        "compare_server_default": True,
        "render_as_batch": is_sqlite(normalize_database_url(settings.DATABASE_URL)),
        "render_item": render_item,
    }


def run_migrations_offline() -> None:
    context.configure(
        url=normalize_database_url(settings.DATABASE_URL),
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        **_context_options(),
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, **_context_options())

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = build_engine()

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
