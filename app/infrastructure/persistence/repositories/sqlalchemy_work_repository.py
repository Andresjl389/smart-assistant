from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.work import WorkSession
from app.domain.repositories.work_repository import WorkSessionRepository
from app.infrastructure.persistence.mappers.work_mapper import WorkSessionMapper
from app.infrastructure.persistence.models.work.work_session import (
    WorkSession as WorkSessionModel,
)


class SqlAlchemyWorkSessionRepository(WorkSessionRepository):

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, work_session: WorkSession) -> WorkSession:
        model = WorkSessionMapper.to_model(work_session)
        self.session.add(model)
        await self.session.flush()

        return WorkSessionMapper.to_domain(model)

    async def get(self, session_id: int) -> WorkSession | None:
        model = await self.session.get(WorkSessionModel, session_id)

        return WorkSessionMapper.to_domain(model) if model else None

    async def get_open(self) -> WorkSession | None:
        result = await self.session.execute(
            select(WorkSessionModel)
            .where(WorkSessionModel.ended_at.is_(None))
            .order_by(WorkSessionModel.started_at.desc())
            .limit(1),
        )
        model = result.scalar_one_or_none()

        return WorkSessionMapper.to_domain(model) if model else None

    async def update(self, work_session: WorkSession) -> WorkSession | None:
        model = await self.session.get(WorkSessionModel, work_session.id)

        if model is None:
            return None

        model.started_at = work_session.started_at
        model.ended_at = work_session.ended_at
        model.minutes = work_session.minutes
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
        )

        statement = self._apply_period(statement, since, until)
        result = await self.session.execute(statement)

        return [WorkSessionMapper.to_domain(model) for model in result.scalars()]

    async def total_minutes(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> int:
        statement = select(func.sum(WorkSessionModel.minutes))
        statement = self._apply_period(statement, since, until)
        result = await self.session.execute(statement)

        return result.scalar() or 0

    async def delete(self, session_id: int) -> bool:
        result = await self.session.execute(
            delete(WorkSessionModel).where(WorkSessionModel.id == session_id),
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
