from datetime import UTC, datetime
from decimal import Decimal

from app.application.dtos.finance.finance_dto import (
    AccountCreateDTO,
    CategoryCreateDTO,
    MovementCreateDTO,
    TransferCreateDTO,
)
from app.domain.entities.finance import (
    Account,
    AccountBalance,
    Category,
    Movement,
    MovementSummary,
)
from app.domain.exceptions.domain_error import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.domain.repositories.finance_repository import (
    AccountRepository,
    CategoryRepository,
    MovementRepository,
)
from app.domain.value_objects.movement_type import MovementType


class ManageFinanceUseCase:

    def __init__(
        self,
        movement_repository: MovementRepository,
        category_repository: CategoryRepository,
        account_repository: AccountRepository,
    ):
        self.movement_repository = movement_repository
        self.category_repository = category_repository
        self.account_repository = account_repository

    async def create_account(self, data: AccountCreateDTO) -> Account:
        if await self.account_repository.get_by_name(data.name):
            raise ConflictError(f"Ya existe una cuenta llamada '{data.name}'.")

        return await self.account_repository.add(
            Account(
                name=data.name,
                type=data.type,
                currency=data.currency.upper(),
                initial_balance=data.initial_balance,
                is_active=data.is_active,
            ),
        )

    async def list_accounts(self, only_active: bool = False) -> list[Account]:
        return await self.account_repository.list(only_active=only_active)

    async def list_account_balances(
        self,
        only_active: bool = False,
    ) -> list[AccountBalance]:
        return await self.account_repository.list_with_balance(
            only_active=only_active,
        )

    async def get_account_balance(self, account_id: int) -> Decimal:
        await self._require_account(account_id)

        return await self.account_repository.balance(account_id)

    async def delete_account(self, account_id: int) -> None:
        await self._require_account(account_id)

        if await self.account_repository.has_movements(account_id):
            raise ConflictError(
                f"La cuenta {account_id} tiene movimientos asociados. "
                "Desactivala en vez de borrarla para no perder historial.",
            )

        await self.account_repository.delete(account_id)

    async def create_category(self, data: CategoryCreateDTO) -> Category:
        if await self.category_repository.get_by_name(data.name):
            raise ConflictError(f"Ya existe una categoria llamada '{data.name}'.")

        return await self.category_repository.add(
            Category(name=data.name, is_active=data.is_active),
        )

    async def list_categories(self, only_active: bool = False) -> list[Category]:
        return await self.category_repository.list(only_active=only_active)

    async def delete_category(self, category_id: int) -> None:
        if not await self.category_repository.delete(category_id):
            raise NotFoundError(f"No existe la categoria {category_id}.")

    async def register_movement(self, data: MovementCreateDTO) -> Movement:
        account = await self._require_account(data.account_id)

        if data.category_id is not None:
            category = await self.category_repository.get(data.category_id)

            if category is None:
                raise NotFoundError(f"No existe la categoria {data.category_id}.")

        return await self.movement_repository.add(
            Movement(
                type=data.type,
                amount=data.amount,
                occurred_at=data.occurred_at or datetime.now(UTC),
                account_id=account.id,
                currency=account.currency,
                description=data.description,
                category_id=data.category_id,
            ),
        )

    async def register_transfer(self, data: TransferCreateDTO) -> Movement:
        if data.from_account_id == data.to_account_id:
            raise ValidationError("El origen y el destino deben ser distintos.")

        origin = await self._require_account(data.from_account_id)
        destination = await self._require_account(data.to_account_id)

        if origin.currency != destination.currency:
            raise ValidationError(
                f"No se puede transferir entre monedas distintas "
                f"({origin.currency} -> {destination.currency}).",
            )

        return await self.movement_repository.add(
            Movement(
                type=MovementType.TRANSFER,
                amount=data.amount,
                occurred_at=data.occurred_at or datetime.now(UTC),
                account_id=origin.id,
                counter_account_id=destination.id,
                currency=origin.currency,
                description=data.description,
            ),
        )

    async def list_movements(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
        movement_type: MovementType | None = None,
        category_id: int | None = None,
        account_id: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Movement]:
        return await self.movement_repository.list(
            since=since,
            until=until,
            movement_type=movement_type,
            category_id=category_id,
            account_id=account_id,
            limit=limit,
            offset=offset,
        )

    async def get_summary(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
        account_id: int | None = None,
    ) -> MovementSummary:
        return await self.movement_repository.summary(
            since=since,
            until=until,
            account_id=account_id,
        )

    async def delete_movement(self, movement_id: int) -> None:
        if not await self.movement_repository.delete(movement_id):
            raise NotFoundError(f"No existe el movimiento {movement_id}.")

    async def _require_account(self, account_id: int) -> Account:
        account = await self.account_repository.get(account_id)

        if account is None:
            raise NotFoundError(f"No existe la cuenta {account_id}.")

        return account
