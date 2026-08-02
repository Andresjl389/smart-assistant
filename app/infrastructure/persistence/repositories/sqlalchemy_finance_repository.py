from datetime import datetime
from decimal import Decimal

from sqlalchemy import case, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.finance import (
    Account,
    AccountBalance,
    Category,
    Movement,
    MovementSummary,
)
from app.domain.repositories.finance_repository import (
    AccountRepository,
    CategoryRepository,
    MovementRepository,
)
from app.domain.value_objects.movement_type import MovementType
from app.infrastructure.persistence.mappers.finance_mapper import (
    AccountMapper,
    CategoryMapper,
    MovementMapper,
    to_amount,
)
from app.infrastructure.persistence.models.finance.account import (
    Account as AccountModel,
)
from app.infrastructure.persistence.models.finance.category import (
    Category as CategoryModel,
)
from app.infrastructure.persistence.models.finance.movement import (
    Movement as MovementModel,
)


OUTGOING_CENTS = case(
    (MovementModel.type == MovementType.INCOME, MovementModel.amount_cents),
    else_=-MovementModel.amount_cents,
)


class SqlAlchemyAccountRepository(AccountRepository):

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, account: Account) -> Account:
        model = AccountMapper.to_model(account)
        self.session.add(model)
        await self.session.flush()

        return AccountMapper.to_domain(model)

    async def get(self, account_id: int) -> Account | None:
        model = await self.session.get(AccountModel, account_id)

        return AccountMapper.to_domain(model) if model else None

    async def get_by_name(self, name: str) -> Account | None:
        result = await self.session.execute(
            select(AccountModel).where(AccountModel.name == name),
        )
        model = result.scalar_one_or_none()

        return AccountMapper.to_domain(model) if model else None

    async def list(self, only_active: bool = False) -> list[Account]:
        statement = select(AccountModel).order_by(AccountModel.name)

        if only_active:
            statement = statement.where(AccountModel.is_active.is_(True))

        result = await self.session.execute(statement)

        return [AccountMapper.to_domain(model) for model in result.scalars()]

    async def balance(self, account_id: int) -> Decimal:
        account = await self.get(account_id)

        if account is None:
            return Decimal(0)

        own = await self.session.execute(
            select(func.sum(OUTGOING_CENTS)).where(
                MovementModel.account_id == account_id,
            ),
        )
        incoming = await self.session.execute(
            select(func.sum(MovementModel.amount_cents)).where(
                MovementModel.counter_account_id == account_id,
                MovementModel.type == MovementType.TRANSFER,
            ),
        )

        return (
            account.initial_balance
            + to_amount(own.scalar())
            + to_amount(incoming.scalar())
        )

    async def list_with_balance(
        self,
        only_active: bool = False,
    ) -> list[AccountBalance]:
        accounts = await self.list(only_active=only_active)

        own_result = await self.session.execute(
            select(MovementModel.account_id, func.sum(OUTGOING_CENTS)).group_by(
                MovementModel.account_id,
            ),
        )
        incoming_result = await self.session.execute(
            select(
                MovementModel.counter_account_id,
                func.sum(MovementModel.amount_cents),
            )
            .where(MovementModel.type == MovementType.TRANSFER)
            .group_by(MovementModel.counter_account_id),
        )

        own = dict(own_result.all())
        incoming = dict(incoming_result.all())

        return [
            AccountBalance(
                account=account,
                balance=(
                    account.initial_balance
                    + to_amount(own.get(account.id))
                    + to_amount(incoming.get(account.id))
                ),
            )
            for account in accounts
        ]

    async def has_movements(self, account_id: int) -> bool:
        result = await self.session.execute(
            select(func.count())
            .select_from(MovementModel)
            .where(
                or_(
                    MovementModel.account_id == account_id,
                    MovementModel.counter_account_id == account_id,
                ),
            ),
        )

        return (result.scalar() or 0) > 0

    async def delete(self, account_id: int) -> bool:
        result = await self.session.execute(
            delete(AccountModel).where(AccountModel.id == account_id),
        )

        return result.rowcount > 0


class SqlAlchemyCategoryRepository(CategoryRepository):

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, category: Category) -> Category:
        model = CategoryMapper.to_model(category)
        self.session.add(model)
        await self.session.flush()

        return CategoryMapper.to_domain(model)

    async def get(self, category_id: int) -> Category | None:
        model = await self.session.get(CategoryModel, category_id)

        return CategoryMapper.to_domain(model) if model else None

    async def get_by_name(self, name: str) -> Category | None:
        result = await self.session.execute(
            select(CategoryModel).where(CategoryModel.name == name),
        )
        model = result.scalar_one_or_none()

        return CategoryMapper.to_domain(model) if model else None

    async def list(self, only_active: bool = False) -> list[Category]:
        statement = select(CategoryModel).order_by(CategoryModel.name)

        if only_active:
            statement = statement.where(CategoryModel.is_active.is_(True))

        result = await self.session.execute(statement)

        return [CategoryMapper.to_domain(model) for model in result.scalars()]

    async def delete(self, category_id: int) -> bool:
        result = await self.session.execute(
            delete(CategoryModel).where(CategoryModel.id == category_id),
        )

        return result.rowcount > 0


class SqlAlchemyMovementRepository(MovementRepository):

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, movement: Movement) -> Movement:
        model = MovementMapper.to_model(movement)
        self.session.add(model)
        await self.session.flush()

        return MovementMapper.to_domain(model)

    async def get(self, movement_id: int) -> Movement | None:
        model = await self.session.get(MovementModel, movement_id)

        return MovementMapper.to_domain(model) if model else None

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
        statement = (
            select(MovementModel)
            .order_by(MovementModel.occurred_at.desc())
            .limit(limit)
            .offset(offset)
        )

        if movement_type is not None:
            statement = statement.where(MovementModel.type == movement_type)

        if category_id is not None:
            statement = statement.where(MovementModel.category_id == category_id)

        if account_id is not None:
            statement = statement.where(
                or_(
                    MovementModel.account_id == account_id,
                    MovementModel.counter_account_id == account_id,
                ),
            )

        statement = self._apply_period(statement, since, until)
        result = await self.session.execute(statement)

        return [MovementMapper.to_domain(model) for model in result.scalars()]

    async def summary(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
        account_id: int | None = None,
    ) -> MovementSummary:
        statement = (
            select(MovementModel.type, func.sum(MovementModel.amount_cents))
            .where(MovementModel.type != MovementType.TRANSFER)
            .group_by(MovementModel.type)
        )

        if account_id is not None:
            statement = statement.where(MovementModel.account_id == account_id)

        statement = self._apply_period(statement, since, until)
        result = await self.session.execute(statement)
        totals = dict(result.all())

        return MovementSummary(
            income=to_amount(totals.get(MovementType.INCOME)),
            expense=to_amount(totals.get(MovementType.EXPENSE)),
        )

    async def delete(self, movement_id: int) -> bool:
        result = await self.session.execute(
            delete(MovementModel).where(MovementModel.id == movement_id),
        )

        return result.rowcount > 0

    def _apply_period(
        self,
        statement,
        since: datetime | None,
        until: datetime | None,
    ):
        if since is not None:
            statement = statement.where(MovementModel.occurred_at >= since)

        if until is not None:
            statement = statement.where(MovementModel.occurred_at <= until)

        return statement
