from typing import Any

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Error de negocio devuelto por la API."""

    detail: str = Field(description="Mensaje legible para mostrar al usuario.")


class FieldError(BaseModel):
    """Un campo del cuerpo o de la URL que no pasó la validación."""

    loc: list[str | int] = Field(description="Ubicación del campo, p. ej. `[\"body\", \"ended_at\"]`.")
    msg: str = Field(description="Qué está mal en el campo.")
    type: str = Field(description="Código del error de validación.")


class ValidationErrorResponse(BaseModel):
    """Datos inválidos: un mensaje de negocio o la lista de campos con error."""

    detail: str | list[FieldError]


def error_response(description: str, example: str) -> dict[str, Any]:
    """Documenta en OpenAPI una respuesta de error con su ejemplo."""
    return {
        "model": ErrorResponse,
        "description": description,
        "content": {"application/json": {"example": {"detail": example}}},
    }


def validation_error_response(description: str, example: str) -> dict[str, Any]:
    """Documenta un 422, que puede venir de una regla de negocio o del formato."""
    return {
        "model": ValidationErrorResponse,
        "description": description,
        "content": {
            "application/json": {
                "examples": {
                    "regla_de_negocio": {
                        "summary": "Regla de negocio",
                        "value": {"detail": example},
                    },
                    "campo_invalido": {
                        "summary": "Campo faltante o con formato inválido",
                        "value": {
                            "detail": [
                                {
                                    "loc": ["body", "ended_at"],
                                    "msg": "Field required",
                                    "type": "missing",
                                },
                            ],
                        },
                    },
                },
            },
        },
    }
