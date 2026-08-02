import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from sqlalchemy import event, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.shared.config.settings import settings


logger = logging.getLogger(__name__)

MEMORY_DATABASES = (":memory:", "")


def is_sqlite(url: URL) -> bool:
    return url.get_backend_name() == "sqlite"


def build_engine(database_url: str | None = None) -> AsyncEngine:
    url = make_url(database_url or settings.DATABASE_URL)

    if is_sqlite(url):
        _ensure_sqlite_directory(url)

    engine = create_async_engine(
        url,
        echo=settings.DB_ECHO,
        **_engine_options(url),
    )

    if is_sqlite(url):
        _register_sqlite_pragmas(engine)

    logger.info("Motor de base de datos inicializado: %s", url.get_backend_name())

    return engine


def _engine_options(url: URL) -> dict:
    if is_sqlite(url):
        return {"connect_args": {"check_same_thread": False}}

    return {
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_recycle": settings.DB_POOL_RECYCLE,
        "pool_pre_ping": True,
    }


def _ensure_sqlite_directory(url: URL) -> None:
    database = url.database or ""

    if database in MEMORY_DATABASES:
        return

    Path(database).parent.mkdir(parents=True, exist_ok=True)


def _register_sqlite_pragmas(engine: AsyncEngine) -> None:
    @event.listens_for(engine.sync_engine, "connect")
    def _set_pragmas(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()


engine = build_engine()

SessionFactory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        async with session.begin():
            yield session


async def check_connection() -> bool:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception:
        logger.exception("No se pudo conectar a la base de datos")
        return False

    return True


async def dispose_engine() -> None:
    await engine.dispose()
