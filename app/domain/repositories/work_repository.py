from abc import ABC, abstractmethod
from datetime import datetime

from app.domain.entities.work import WorkSession


class WorkSessionRepository(ABC):

    @abstractmethod
    async def add(self, session: WorkSession) -> WorkSession:
        raise NotImplementedError

    @abstractmethod
    async def get(self, session_id: int) -> WorkSession | None:
        raise NotImplementedError

    @abstractmethod
    async def get_open(self) -> WorkSession | None:
        raise NotImplementedError

    @abstractmethod
    async def update(self, session: WorkSession) -> WorkSession | None:
        raise NotImplementedError

    @abstractmethod
    async def list(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[WorkSession]:
        raise NotImplementedError

    @abstractmethod
    async def total_minutes(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> int:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, session_id: int) -> bool:
        raise NotImplementedError
