from fastapi import APIRouter

from app.presentation.api.routes.finance import router as finance_router
from app.presentation.api.routes.webhooks.gmail import router as webhook_router
from app.presentation.api.routes.work import router as work_router

router = APIRouter()

router.include_router(webhook_router)
router.include_router(finance_router)
router.include_router(work_router)
