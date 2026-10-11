from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from app.domain.entities.work import WorkPreferences, WorkSession


class WorkSessionRepository(ABC):

    @abstractmethod
    async def add(self, session: WorkSession) -> WorkSession:
        raise NotImplementedError

    @abstractmethod
    async def get(self, session_id: UUID) -> WorkSession | None:
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
    async def find_overlapping(
        self,
        started_at: datetime,
        ended_at: datetime | None,
        exclude_id: UUID | None = None,
    ) -> WorkSession | None:
        """Devuelve una jornada que se cruce con el intervalo dado, si existe.

        `ended_at=None` representa una jornada abierta (sin fin).
        """
        raise NotImplementedError

    @abstractmethod
    async def delete(self, session_id: UUID) -> bool:
        raise NotImplementedError


class WorkPreferencesRepository(ABC):

    @abstractmethod
    async def get(self) -> WorkPreferences | None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, preferences: WorkPreferences) -> WorkPreferences:
        raise NotImplementedError
