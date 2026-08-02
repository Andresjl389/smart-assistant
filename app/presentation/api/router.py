from fastapi import APIRouter

from app.presentation.api.routes.webhooks.gmail import router as webhook_router

router = APIRouter()

router.include_router(webhook_router)