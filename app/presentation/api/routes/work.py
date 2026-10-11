from datetime import date, datetime
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Path, Query, Response, status

from app.application.dtos.work.work_dto import (
    WorkPreferencesDTO,
    WorkPreferencesUpdateDTO,
    WorkSessionCreateDTO,
    WorkSessionDTO,
    WorkSessionStartDTO,
    WorkSessionStopDTO,
    WorkSessionUpdateDTO,
    WorkSummaryDTO,
    WorkWeekDTO,
)
from app.application.use_cases.track_work import TrackWorkUseCase
from app.presentation.api.dependencies.use_cases import get_track_work_use_case
from app.presentation.api.dependencies.security import get_current_user
from app.presentation.api.responses import error_response, validation_error_response


router = APIRouter(
    prefix="/work",
    tags=["Horas trabajadas"],
    dependencies=[Depends(get_current_user)],
    responses={
        status.HTTP_401_UNAUTHORIZED: error_response(
            "No hay una sesión iniciada o ya venció.",
            "Inicia sesión.",
        ),
    },
)

SESSION_NOT_FOUND = error_response(
    "La jornada no existe o pertenece a otro usuario.",
    "No existe la jornada 3fa85f64-5717-4562-b3fc-2c963f66afa6.",
)
SESSION_OVERLAP = error_response(
    "Las horas se cruzan con otra jornada registrada.",
    "Se cruza con la jornada 3fa85f64-5717-4562-b3fc-2c963f66afa6, "
    "de 2026-10-05T13:00:00+00:00 a 2026-10-05T22:00:00+00:00.",
)
SESSION_INVALID = validation_error_response(
    "Los datos no cumplen las reglas de la jornada (formato, salida antes "
    "del ingreso, más de 24 horas o descanso mayor que la jornada).",
    "La jornada no puede terminar antes de empezar.",
)
SESSION_ID = Path(description="Identificador de la jornada.")


@router.post(
    "/sessions/start",
    response_model=WorkSessionDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Marcar entrada",
    description=(
        "Abre una jornada. Sin cuerpo usa la hora actual; con `started_at` "
        "registra una entrada pasada. Solo puede haber una jornada abierta."
    ),
    response_description="La jornada abierta.",
    responses={
        status.HTTP_409_CONFLICT: error_response(
            "Ya hay una jornada abierta o la hora se cruza con otra jornada.",
            "Ya hay una jornada abierta (id 3fa85f64-5717-4562-b3fc-2c963f66afa6) "
            "desde 2026-10-05T13:00:00+00:00. Cierrala primero.",
        ),
        status.HTTP_422_UNPROCESSABLE_CONTENT: SESSION_INVALID,
    },
)
async def start_session(
    payload: WorkSessionStartDTO | None = None,
    use_case: TrackWorkUseCase = Depends(get_track_work_use_case),
):
    return await use_case.start_session(payload or WorkSessionStartDTO())


@router.post(
    "/sessions/stop",
    response_model=WorkSessionDTO,
    summary="Marcar salida",
    description=(
        "Cierra la jornada abierta y calcula los minutos netos "
        "(salida − ingreso − descanso). Sin cuerpo usa la hora actual."
    ),
    response_description="La jornada cerrada con sus tiempos calculados.",
    responses={
        status.HTTP_404_NOT_FOUND: error_response(
            "No hay ninguna jornada abierta.",
            "No hay ninguna jornada abierta para cerrar.",
        ),
        status.HTTP_409_CONFLICT: SESSION_OVERLAP,
        status.HTTP_422_UNPROCESSABLE_CONTENT: SESSION_INVALID,
    },
)
async def stop_session(
    payload: WorkSessionStopDTO | None = None,
    use_case: TrackWorkUseCase = Depends(get_track_work_use_case),
):
    return await use_case.stop_session(payload or WorkSessionStopDTO())


@router.get(
    "/sessions/current",
    response_model=WorkSessionDTO | None,
    summary="Jornada abierta",
    description="Devuelve la jornada sin salida, o `204` si no hay ninguna.",
    responses={status.HTTP_204_NO_CONTENT: {"description": "No hay jornada abierta."}},
)
async def get_current_session(
    response: Response,
    use_case: TrackWorkUseCase = Depends(get_track_work_use_case),
):
    session = await use_case.get_current_session()

    if session is None:
        response.status_code = status.HTTP_204_NO_CONTENT

    return session


@router.post(
    "/sessions",
    response_model=WorkSessionDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar jornada con ingreso y salida",
    description=(
        "Registra una jornada ya terminada indicando la hora de ingreso y de "
        "salida. `started_at` y `ended_at` son obligatorios; el descanso se "
        "descuenta del tiempo trabajado."
    ),
    response_description="La jornada creada con sus tiempos calculados.",
    responses={
        status.HTTP_409_CONFLICT: SESSION_OVERLAP,
        status.HTTP_422_UNPROCESSABLE_CONTENT: SESSION_INVALID,
    },
)
async def register_session(
    payload: WorkSessionCreateDTO = Body(
        openapi_examples={
            "con_almuerzo": {
                "summary": "Jornada con una hora de almuerzo",
                "value": {
                    "started_at": "2026-10-05T08:00:00-05:00",
                    "ended_at": "2026-10-05T17:00:00-05:00",
                    "break_minutes": 60,
                    "note": "Oficina",
                },
            },
            "sin_descanso": {
                "summary": "Media jornada sin descanso",
                "value": {
                    "started_at": "2026-10-06T08:00:00-05:00",
                    "ended_at": "2026-10-06T12:30:00-05:00",
                },
            },
            "turno_nocturno": {
                "summary": "Turno que termina después de medianoche",
                "value": {
                    "started_at": "2026-10-07T22:00:00-05:00",
                    "ended_at": "2026-10-08T06:00:00-05:00",
                    "break_minutes": 30,
                },
            },
        },
    ),
    use_case: TrackWorkUseCase = Depends(get_track_work_use_case),
):
    return await use_case.register_session(payload)


@router.get(
    "/sessions",
    response_model=list[WorkSessionDTO],
    summary="Listar jornadas",
    description="Jornadas ordenadas de la más reciente a la más antigua.",
)
async def list_sessions(
    since: datetime | None = Query(
        default=None,
        description="Solo jornadas que empezaron desde esta fecha (con zona horaria).",
        examples=["2026-10-05T00:00:00-05:00"],
    ),
    until: datetime | None = Query(
        default=None,
        description="Solo jornadas que empezaron hasta esta fecha (con zona horaria).",
        examples=["2026-10-11T23:59:59-05:00"],
    ),
    limit: int = Query(default=100, ge=1, le=500, description="Máximo de resultados."),
    offset: int = Query(default=0, ge=0, description="Resultados a saltar."),
    use_case: TrackWorkUseCase = Depends(get_track_work_use_case),
):
    return await use_case.list_sessions(
        since=since,
        until=until,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/sessions/{session_id}",
    response_model=WorkSessionDTO,
    summary="Consultar jornada",
    responses={status.HTTP_404_NOT_FOUND: SESSION_NOT_FOUND},
)
async def get_session(
    session_id: UUID = SESSION_ID,
    use_case: TrackWorkUseCase = Depends(get_track_work_use_case),
):
    return await use_case.get_session(session_id)


@router.patch(
    "/sessions/{session_id}",
    response_model=WorkSessionDTO,
    summary="Corregir jornada",
    description=(
        "Modifica solo los campos enviados y recalcula los tiempos. Enviar "
        "`ended_at` a una jornada abierta la cierra; `note: null` borra la nota."
    ),
    response_description="La jornada con sus tiempos recalculados.",
    responses={
        status.HTTP_404_NOT_FOUND: SESSION_NOT_FOUND,
        status.HTTP_409_CONFLICT: SESSION_OVERLAP,
        status.HTTP_422_UNPROCESSABLE_CONTENT: SESSION_INVALID,
    },
)
async def update_session(
    payload: WorkSessionUpdateDTO,
    session_id: UUID = SESSION_ID,
    use_case: TrackWorkUseCase = Depends(get_track_work_use_case),
):
    return await use_case.update_session(session_id, payload)


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar jornada",
    responses={status.HTTP_404_NOT_FOUND: SESSION_NOT_FOUND},
)
async def delete_session(
    session_id: UUID = SESSION_ID,
    use_case: TrackWorkUseCase = Depends(get_track_work_use_case),
):
    await use_case.delete_session(session_id)


@router.get(
    "/summary",
    response_model=WorkSummaryDTO,
    summary="Totales por periodo",
    description="Suma las jornadas cerradas que empezaron dentro del periodo.",
)
async def get_summary(
    since: datetime | None = Query(
        default=None,
        description="Inicio del periodo (con zona horaria).",
        examples=["2026-10-01T00:00:00-05:00"],
    ),
    until: datetime | None = Query(
        default=None,
        description="Fin del periodo (con zona horaria).",
        examples=["2026-10-31T23:59:59-05:00"],
    ),
    use_case: TrackWorkUseCase = Depends(get_track_work_use_case),
):
    return await use_case.get_summary(since=since, until=until)


@router.get(
    "/week",
    response_model=WorkWeekDTO,
    summary="Avance de la semana",
    description=(
        "Horas trabajadas de lunes a domingo frente a la cuota semanal: lo "
        "que falta, horas extra, porcentaje de avance, promedio diario "
        "necesario y detalle por día. Incluye la jornada abierta hasta ahora."
    ),
)
async def get_week(
    day: date | None = Query(
        default=None,
        alias="date",
        description="Cualquier día de la semana a consultar. Por defecto, hoy.",
        examples=["2026-10-08"],
    ),
    use_case: TrackWorkUseCase = Depends(get_track_work_use_case),
):
    return await use_case.get_week(day)


@router.get(
    "/preferences",
    response_model=WorkPreferencesDTO,
    summary="Consultar preferencias",
    description=(
        "Cuota semanal, zona horaria y días laborales. Si el usuario no las "
        "configuró, devuelve los valores por defecto del servidor."
    ),
)
async def get_preferences(
    use_case: TrackWorkUseCase = Depends(get_track_work_use_case),
):
    return await use_case.get_preferences()


@router.patch(
    "/preferences",
    response_model=WorkPreferencesDTO,
    summary="Cambiar preferencias",
    description="Modifica solo los campos enviados.",
)
async def update_preferences(
    payload: WorkPreferencesUpdateDTO,
    use_case: TrackWorkUseCase = Depends(get_track_work_use_case),
):
    return await use_case.update_preferences(payload)
