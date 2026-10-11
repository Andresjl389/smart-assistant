from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.work import WorkPreferences, WorkSession
from app.domain.repositories.work_repository import (
    WorkPreferencesRepository,
    WorkSessionRepository,
)
from app.infrastructure.persistence.mappers.work_mapper import (
    WorkPreferencesMapper,
    WorkSessionMapper,
)
from app.infrastructure.persistence.models.work.work_preferences import (
    WorkPreferences as WorkPreferencesModel,
)
from app.infrastructure.persistence.models.work.work_session import (
    WorkSession as WorkSessionModel,
)


class SqlAlchemyWorkSessionRepository(WorkSessionRepository):

    def __init__(self, session: AsyncSession, user_id: UUID):
        self.session = session
        self.user_id = user_id

    async def add(self, work_session: WorkSession) -> WorkSession:
        model = WorkSessionMapper.to_model(work_session)
        model.user_id = self.user_id
        self.session.add(model)
        await self.session.flush()

        return WorkSessionMapper.to_domain(model)

    async def get(self, session_id: UUID) -> WorkSession | None:
        model = await self.session.scalar(select(WorkSessionModel).where(WorkSessionModel.id == session_id, WorkSessionModel.user_id == self.user_id))

        return WorkSessionMapper.to_domain(model) if model else None

    async def get_open(self) -> WorkSession | None:
        result = await self.session.execute(
            select(WorkSessionModel)
            .where(WorkSessionModel.ended_at.is_(None), WorkSessionModel.user_id == self.user_id)
            .order_by(WorkSessionModel.started_at.desc())
            .limit(1),
        )
        model = result.scalar_one_or_none()

        return WorkSessionMapper.to_domain(model) if model else None

    async def update(self, work_session: WorkSession) -> WorkSession | None:
        model = await self.session.scalar(select(WorkSessionModel).where(WorkSessionModel.id == work_session.id, WorkSessionModel.user_id == self.user_id))

        if model is None:
            return None

        model.started_at = work_session.started_at
        model.ended_at = work_session.ended_at
        model.minutes = work_session.minutes
        model.break_minutes = work_session.break_minutes
        model.note = work_session.note
        await self.session.flush()

        return WorkSessionMapper.to_domain(model)

    async def list(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[WorkSession]:
        statement = (
            select(WorkSessionModel)
            .order_by(WorkSessionModel.started_at.desc())
            .limit(limit)
            .offset(offset)
            .where(WorkSessionModel.user_id == self.user_id)
        )

        statement = self._apply_period(statement, since, until)
        result = await self.session.execute(statement)

        return [WorkSessionMapper.to_domain(model) for model in result.scalars()]

    async def total_minutes(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> int:
        statement = select(func.sum(WorkSessionModel.minutes)).where(WorkSessionModel.user_id == self.user_id)
        statement = self._apply_period(statement, since, until)
        result = await self.session.execute(statement)

        return result.scalar() or 0

    async def find_overlapping(
        self,
        started_at: datetime,
        ended_at: datetime | None,
        exclude_id: UUID | None = None,
    ) -> WorkSession | None:
        statement = (
            select(WorkSessionModel)
            .where(
                WorkSessionModel.user_id == self.user_id,
                or_(
                    WorkSessionModel.ended_at.is_(None),
                    WorkSessionModel.ended_at > started_at,
                ),
            )
            .order_by(WorkSessionModel.started_at)
            .limit(1)
        )

        if ended_at is not None:
            statement = statement.where(WorkSessionModel.started_at < ended_at)

        if exclude_id is not None:
            statement = statement.where(WorkSessionModel.id != exclude_id)

        model = await self.session.scalar(statement)

        return WorkSessionMapper.to_domain(model) if model else None

    async def delete(self, session_id: UUID) -> bool:
        result = await self.session.execute(
            delete(WorkSessionModel).where(WorkSessionModel.id == session_id, WorkSessionModel.user_id == self.user_id),
        )

        return result.rowcount > 0

    def _apply_period(
        self,
        statement,
        since: datetime | None,
        until: datetime | None,
    ):
        if since is not None:
            statement = statement.where(WorkSessionModel.started_at >= since)

        if until is not None:
            statement = statement.where(WorkSessionModel.started_at <= until)

        return statement


class SqlAlchemyWorkPreferencesRepository(WorkPreferencesRepository):

    def __init__(self, session: AsyncSession, user_id: UUID):
        self.session = session
        self.user_id = user_id

    async def get(self) -> WorkPreferences | None:
        model = await self.session.get(WorkPreferencesModel, self.user_id)

        return WorkPreferencesMapper.to_domain(model) if model else None

    async def save(self, preferences: WorkPreferences) -> WorkPreferences:
        model = await self.session.get(WorkPreferencesModel, self.user_id)

        if model is None:
            model = WorkPreferencesModel(user_id=self.user_id)
            self.session.add(model)

        model.weekly_target_minutes = preferences.weekly_target_minutes
        model.timezone = preferences.timezone
        model.work_days = WorkPreferencesMapper.serialize_work_days(
            preferences.work_days,
        )
        await self.session.flush()

        return WorkPreferencesMapper.to_domain(model)
