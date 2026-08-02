from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.infrastructure.persistence.database import check_connection, dispose_engine
from app.presentation.api.exception_handlers import register_exception_handlers
from app.presentation.api.router import router
from app.presentation.middleware.cors import register_cors


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await dispose_engine()


app = FastAPI(
    title="Smart Assistant",
    version="0.1.0",
    lifespan=lifespan,
)

register_cors(app)
register_exception_handlers(app)
app.include_router(router)


@app.get("/health", tags=["Health"])
async def health():
    database_ok = await check_connection()

    return {
        "status": "ok" if database_ok else "degraded",
        "message": "Smart Assistant is running",
        "database": "ok" if database_ok else "unreachable",
    }
