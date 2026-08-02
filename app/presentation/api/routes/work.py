from datetime import datetime

from fastapi import APIRouter, Depends, Query, Response, status

from app.application.dtos.work.work_dto import (
    WorkSessionDTO,
    WorkSessionStartDTO,
    WorkSessionStopDTO,
    WorkSummaryDTO,
)
from app.application.use_cases.track_work import TrackWorkUseCase
from app.presentation.api.dependencies.use_cases import get_track_work_use_case


router = APIRouter(prefix="/work", tags=["Horas trabajadas"])


@router.post(
    "/sessions/start",
    response_model=WorkSessionDTO,
    status_code=status.HTTP_201_CREATED,
)
async def start_session(
    payload: WorkSessionStartDTO | None = None,
    use_case: TrackWorkUseCase = Depends(get_track_work_use_case),
):
    return await use_case.start_session(payload or WorkSessionStartDTO())


@router.post("/sessions/stop", response_model=WorkSessionDTO)
async def stop_session(
    payload: WorkSessionStopDTO | None = None,
    use_case: TrackWorkUseCase = Depends(get_track_work_use_case),
):
    return await use_case.stop_session(payload or WorkSessionStopDTO())


@router.get("/sessions/current", response_model=WorkSessionDTO | None)
async def get_current_session(
    response: Response,
    use_case: TrackWorkUseCase = Depends(get_track_work_use_case),
):
    session = await use_case.get_current_session()

    if session is None:
        response.status_code = status.HTTP_204_NO_CONTENT

    return session


@router.get("/sessions", response_model=list[WorkSessionDTO])
async def list_sessions(
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    use_case: TrackWorkUseCase = Depends(get_track_work_use_case),
):
    return await use_case.list_sessions(
        since=since,
        until=until,
        limit=limit,
        offset=offset,
    )


@router.get("/summary", response_model=WorkSummaryDTO)
async def get_summary(
    since: datetime | None = None,
    until: datetime | None = None,
    use_case: TrackWorkUseCase = Depends(get_track_work_use_case),
):
    return await use_case.get_summary(since=since, until=until)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: int,
    use_case: TrackWorkUseCase = Depends(get_track_work_use_case),
):
    await use_case.delete_session(session_id)
