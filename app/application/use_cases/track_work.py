from datetime import UTC, datetime

from app.application.dtos.work.work_dto import (
    WorkSessionStartDTO,
    WorkSessionStopDTO,
)
from app.domain.entities.work import MINUTES_PER_HOUR, WorkSession
from app.domain.exceptions.domain_error import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.domain.repositories.work_repository import WorkSessionRepository


class TrackWorkUseCase:

    def __init__(self, work_session_repository: WorkSessionRepository):
        self.work_session_repository = work_session_repository

    async def start_session(self, data: WorkSessionStartDTO) -> WorkSession:
        open_session = await self.work_session_repository.get_open()

        if open_session:
            raise ConflictError(
                f"Ya hay una jornada abierta (id {open_session.id}) "
                f"desde {open_session.started_at.isoformat()}. Cierrala primero.",
            )

        return await self.work_session_repository.add(
            WorkSession(
                started_at=data.started_at or datetime.now(UTC),
                note=data.note,
            ),
        )

    async def stop_session(self, data: WorkSessionStopDTO) -> WorkSession:
        open_session = await self.work_session_repository.get_open()

        if open_session is None:
            raise NotFoundError("No hay ninguna jornada abierta para cerrar.")

        try:
            open_session.close(data.ended_at)
        except ValueError as error:
            raise ValidationError(str(error)) from error

        updated = await self.work_session_repository.update(open_session)

        if updated is None:
            raise NotFoundError(f"No existe la jornada {open_session.id}.")

        return updated

    async def get_current_session(self) -> WorkSession | None:
        return await self.work_session_repository.get_open()

    async def list_sessions(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[WorkSession]:
        return await self.work_session_repository.list(
            since=since,
            until=until,
            limit=limit,
            offset=offset,
        )

    async def get_summary(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> dict:
        total_minutes = await self.work_session_repository.total_minutes(
            since=since,
            until=until,
        )
        sessions = await self.work_session_repository.list(
            since=since,
            until=until,
            limit=1000,
        )

        return {
            "total_minutes": total_minutes,
            "total_hours": round(total_minutes / MINUTES_PER_HOUR, 2),
            "sessions": len(sessions),
        }

    async def delete_session(self, session_id: int) -> None:
        if not await self.work_session_repository.delete(session_id):
            raise NotFoundError(f"No existe la jornada {session_id}.")
