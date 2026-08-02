import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.shared.config.settings import settings


logger = logging.getLogger(__name__)

ANY_ORIGIN = "*"
ANY_ORIGIN_REGEX = ".*"


def register_cors(app: FastAPI) -> None:
    origins = settings.cors_origins
    allow_all = ANY_ORIGIN in origins

    options = {
        "allow_credentials": settings.CORS_ALLOW_CREDENTIALS,
        "allow_methods": settings.cors_allow_methods,
        "allow_headers": settings.cors_allow_headers,
        "expose_headers": ["*"],
        "max_age": settings.CORS_MAX_AGE,
    }

    if allow_all and settings.CORS_ALLOW_CREDENTIALS:
        # El estandar prohibe combinar "*" con credenciales: el navegador
        # exige el origen concreto. El regex hace que se refleje el origen
        # de cada peticion en vez de responder con el comodin.
        options["allow_origins"] = []
        options["allow_origin_regex"] = ANY_ORIGIN_REGEX
    else:
        options["allow_origins"] = origins

    app.add_middleware(CORSMiddleware, **options)

    logger.info(
        "CORS habilitado. Origenes: %s | credenciales: %s",
        origins,
        settings.CORS_ALLOW_CREDENTIALS,
    )
