from fastapi import FastAPI

from app.presentation.api.router import router

app = FastAPI(
    title="Smart Assistant",
    version="0.1.0",
)

app.include_router(router)


@app.get("/health", tags=["Health"])
async def health():
    return {
        "status": "ok",
        "message": "Smart Assistant is running",
    }