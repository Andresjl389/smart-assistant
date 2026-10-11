from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from app.application.dtos.work.work_dto import (
    WorkPreferencesUpdateDTO,
    WorkSessionCreateDTO,
    WorkSessionStartDTO,
    WorkSessionStopDTO,
    WorkSessionUpdateDTO,
)
from app.domain.entities.work import (
    MINUTES_PER_HOUR,
    WorkPreferences,
    WorkSession,
    WorkWeek,
)
from app.domain.exceptions.domain_error import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.domain.repositories.work_repository import (
    WorkPreferencesRepository,
    WorkSessionRepository,
)
from app.shared.config.settings import settings


MAX_SESSIONS_PER_WEEK = 1000


class TrackWorkUseCase:

    def __init__(
        self,
        work_session_repository: WorkSessionRepository,
        work_preferences_repository: WorkPreferencesRepository,
    ):
        self.work_session_repository = work_session_repository
        self.work_preferences_repository = work_preferences_repository

    async def start_session(self, data: WorkSessionStartDTO) -> WorkSession:
        open_session = await self.work_session_repository.get_open()

        if open_session:
            raise ConflictError(
                f"Ya hay una jornada abierta (id {open_session.id}) "
                f"desde {open_session.started_at.isoformat()}. Cierrala primero.",
            )

        session = WorkSession(
            started_at=data.started_at or datetime.now(UTC),
            note=data.note,
        )
        await self._ensure_no_overlap(session)

        return await self.work_session_repository.add(session)

    async def stop_session(self, data: WorkSessionStopDTO) -> WorkSession:
        open_session = await self.work_session_repository.get_open()

        if open_session is None:
            raise NotFoundError("No hay ninguna jornada abierta para cerrar.")

        try:
            open_session.close(data.ended_at, data.break_minutes)
        except ValueError as error:
            raise ValidationError(str(error)) from error

        await self._ensure_no_overlap(open_session)

        return await self._save(open_session)

    async def register_session(self, data: WorkSessionCreateDTO) -> WorkSession:
        session = WorkSession(started_at=data.started_at, note=data.note)

        try:
            session.reschedule(
                ended_at=data.ended_at,
                break_minutes=data.break_minutes,
            )
        except ValueError as error:
            raise ValidationError(str(error)) from error

        await self._ensure_no_overlap(session)

        return await self.work_session_repository.add(session)

    async def update_session(
        self,
        session_id: UUID,
        data: WorkSessionUpdateDTO,
    ) -> WorkSession:
        session = await self.get_session(session_id)
        changes = data.model_dump(exclude_unset=True)

        if "note" in changes:
            session.note = changes["note"]

        try:
            session.reschedule(
                started_at=changes.get("started_at"),
                ended_at=changes.get("ended_at"),
                break_minutes=changes.get("break_minutes"),
            )
        except ValueError as error:
            raise ValidationError(str(error)) from error

        await self._ensure_no_overlap(session)

        return await self._save(session)

    async def get_session(self, session_id: UUID) -> WorkSession:
        session = await self.work_session_repository.get(session_id)

        if session is None:
            raise NotFoundError(f"No existe la jornada {session_id}.")

        return session

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

    async def get_week(self, reference: date | None = None) -> WorkWeek:
        preferences = await self.get_preferences()
        now = datetime.now(UTC)
        reference = reference or now.astimezone(preferences.tzinfo).date()
        since, until = WorkWeek.bounds(reference, preferences)
        sessions = await self.work_session_repository.list(
            since=since,
            until=until - timedelta(microseconds=1),
            limit=MAX_SESSIONS_PER_WEEK,
        )

        return WorkWeek.build(reference, sessions, preferences, now)

    async def get_preferences(self) -> WorkPreferences:
        preferences = await self.work_preferences_repository.get()

        if preferences is not None:
            return preferences

        return WorkPreferences(
            weekly_target_minutes=round(
                settings.WORK_WEEKLY_TARGET_HOURS * MINUTES_PER_HOUR,
            ),
            timezone=settings.WORK_TIMEZONE,
            work_days=settings.work_days,
        )

    async def update_preferences(
        self,
        data: WorkPreferencesUpdateDTO,
    ) -> WorkPreferences:
        preferences = await self.get_preferences()

        if data.weekly_target_hours is not None:
            preferences.weekly_target_minutes = round(
                data.weekly_target_hours * MINUTES_PER_HOUR,
            )

        if data.timezone is not None:
            preferences.timezone = data.timezone

        if data.work_days is not None:
            preferences.work_days = tuple(data.work_days)

        return await self.work_preferences_repository.save(preferences)

    async def delete_session(self, session_id: UUID) -> None:
        if not await self.work_session_repository.delete(session_id):
            raise NotFoundError(f"No existe la jornada {session_id}.")

    async def _ensure_no_overlap(self, session: WorkSession) -> None:
        overlapping = await self.work_session_repository.find_overlapping(
            session.started_at,
            session.ended_at,
            exclude_id=session.id,
        )

        if overlapping is None:
            return

        until = (
            overlapping.ended_at.isoformat()
            if overlapping.ended_at
            else "ahora (sigue abierta)"
        )

        raise ConflictError(
            f"Se cruza con la jornada {overlapping.id}, "
            f"de {overlapping.started_at.isoformat()} a {until}.",
        )

    async def _save(self, session: WorkSession) -> WorkSession:
        updated = await self.work_session_repository.update(session)

        if updated is None:
            raise NotFoundError(f"No existe la jornada {session.id}.")

        return updated
