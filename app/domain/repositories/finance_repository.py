from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal

from app.domain.entities.finance import (
    Account,
    AccountBalance,
    Category,
    Movement,
    MovementSummary,
)
from app.domain.value_objects.movement_type import MovementType


class AccountRepository(ABC):

    @abstractmethod
    async def add(self, account: Account) -> Account:
        raise NotImplementedError

    @abstractmethod
    async def get(self, account_id: int) -> Account | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_name(self, name: str) -> Account | None:
        raise NotImplementedError

    @abstractmethod
    async def list(self, only_active: bool = False) -> list[Account]:
        raise NotImplementedError

    @abstractmethod
    async def balance(self, account_id: int) -> Decimal:
        raise NotImplementedError

    @abstractmethod
    async def list_with_balance(
        self,
        only_active: bool = False,
    ) -> list[AccountBalance]:
        raise NotImplementedError

    @abstractmethod
    async def has_movements(self, account_id: int) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, account_id: int) -> bool:
        raise NotImplementedError


class CategoryRepository(ABC):

    @abstractmethod
    async def add(self, category: Category) -> Category:
        raise NotImplementedError

    @abstractmethod
    async def get(self, category_id: int) -> Category | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_name(self, name: str) -> Category | None:
        raise NotImplementedError

    @abstractmethod
    async def list(self, only_active: bool = False) -> list[Category]:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, category_id: int) -> bool:
        raise NotImplementedError


class MovementRepository(ABC):

    @abstractmethod
    async def add(self, movement: Movement) -> Movement:
        raise NotImplementedError

    @abstractmethod
    async def get(self, movement_id: int) -> Movement | None:
        raise NotImplementedError

    @abstractmethod
    async def list(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
        movement_type: MovementType | None = None,
        category_id: int | None = None,
        account_id: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Movement]:
        raise NotImplementedError

    @abstractmethod
    async def summary(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
        account_id: int | None = None,
    ) -> MovementSummary:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, movement_id: int) -> bool:
        raise NotImplementedError
