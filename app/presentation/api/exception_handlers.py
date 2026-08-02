from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.domain.exceptions.domain_error import (
    ConflictError,
    DomainError,
    NotFoundError,
    ValidationError,
)


STATUS_BY_ERROR = {
    NotFoundError: 404,
    ConflictError: 409,
    ValidationError: 422,
}


def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(DomainError)
    async def handle_domain_error(_request: Request, error: DomainError):
        return JSONResponse(
            status_code=STATUS_BY_ERROR.get(type(error), 400),
            content={"detail": str(error)},
        )
