import logging
import os
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
POSTGRES_PREFIXES = ("postgres://", "postgresql://")
ASYNC_POSTGRES_PREFIX = "postgresql+asyncpg://"
SSL_MODES_REQUIRING_TLS = frozenset({"require", "verify-ca", "verify-full"})


def is_sqlite(url: URL) -> bool:
    return url.get_backend_name() == "sqlite"


def normalize_database_url(database_url: str) -> URL:
    """Adapta la URL que entregan los proveedores gestionados.

    Railway, Heroku y similares publican DATABASE_URL como
    'postgresql://' o 'postgres://', que apuntan a un driver sincrono.
    Sin este ajuste el arranque falla pidiendo psycopg2.
    """
    for prefix in POSTGRES_PREFIXES:
        if database_url.startswith(prefix):
            database_url = ASYNC_POSTGRES_PREFIX + database_url[len(prefix) :]
            break

    return make_url(database_url)


def build_engine(database_url: str | None = None) -> AsyncEngine:
    url = normalize_database_url(database_url or settings.DATABASE_URL)
    url, requires_tls = _extract_ssl_mode(url)

    if is_sqlite(url):
        _ensure_sqlite_directory(url)
        _warn_if_storage_is_ephemeral(url)

    engine = create_async_engine(
        url,
        echo=settings.DB_ECHO,
        **_engine_options(url, requires_tls),
    )

    if is_sqlite(url):
        _register_sqlite_pragmas(engine)

    logger.info("Motor de base de datos inicializado: %s", url.get_backend_name())

    return engine


def _extract_ssl_mode(url: URL) -> tuple[URL, bool]:
    """asyncpg no entiende 'sslmode', que es un parametro de psycopg2."""
    sslmode = url.query.get("sslmode")

    if sslmode is None:
        return url, False

    query = {key: value for key, value in url.query.items() if key != "sslmode"}

    return url.set(query=query), sslmode in SSL_MODES_REQUIRING_TLS


def _engine_options(url: URL, requires_tls: bool = False) -> dict:
    if is_sqlite(url):
        return {"connect_args": {"check_same_thread": False}}

    options = {
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_recycle": settings.DB_POOL_RECYCLE,
        "pool_pre_ping": True,
    }

    if requires_tls:
        options["connect_args"] = {"ssl": True}

    return options


def _warn_if_storage_is_ephemeral(url: URL) -> None:
    """Avisa si el archivo SQLite no vive dentro del volumen persistente.

    Con una ruta relativa el archivo queda en el sistema de archivos del
    contenedor: funciona hasta el siguiente despliegue, cuando los datos
    desaparecen sin ningun error visible.
    """
    mount_path = os.getenv("RAILWAY_VOLUME_MOUNT_PATH")
    database = url.database or ""

    if not mount_path or database in MEMORY_DATABASES:
        return

    if not Path(database).resolve().is_relative_to(Path(mount_path).resolve()):
        logger.warning(
            "La base SQLite (%s) esta fuera del volumen persistente (%s). "
            "Los datos se perderan en el proximo despliegue. Usa una ruta "
            "absoluta con cuatro barras: sqlite+aiosqlite:///%s/archivo.db",
            database,
            mount_path,
            mount_path,
        )


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
