from decimal import Decimal

from app.domain.entities.finance import Account, Category, Movement
from app.infrastructure.persistence.models.finance.account import (
    Account as AccountModel,
)
from app.infrastructure.persistence.models.finance.category import (
    Category as CategoryModel,
)
from app.infrastructure.persistence.models.finance.movement import (
    Movement as MovementModel,
)


CENTS = Decimal(100)


def to_cents(amount: Decimal | int | str) -> int:
    return int((Decimal(amount) * CENTS).to_integral_value())


def to_amount(cents: int | None) -> Decimal:
    return Decimal(cents or 0) / CENTS


class AccountMapper:

    @staticmethod
    def to_domain(model: AccountModel) -> Account:
        return Account(
            id=model.id,
            name=model.name,
            type=model.type,
            currency=model.currency,
            initial_balance=to_amount(model.initial_balance_cents),
            is_active=model.is_active,
        )

    @staticmethod
    def to_model(entity: Account) -> AccountModel:
        return AccountModel(
            id=entity.id,
            name=entity.name,
            type=entity.type,
            currency=entity.currency,
            initial_balance_cents=to_cents(entity.initial_balance),
            is_active=entity.is_active,
        )


class CategoryMapper:

    @staticmethod
    def to_domain(model: CategoryModel) -> Category:
        return Category(
            id=model.id,
            name=model.name,
            is_active=model.is_active,
        )

    @staticmethod
    def to_model(entity: Category) -> CategoryModel:
        return CategoryModel(
            id=entity.id,
            name=entity.name,
            is_active=entity.is_active,
        )


class MovementMapper:

    @staticmethod
    def to_domain(model: MovementModel) -> Movement:
        return Movement(
            id=model.id,
            type=model.type,
            amount=to_amount(model.amount_cents),
            currency=model.currency,
            description=model.description,
            occurred_at=model.occurred_at,
            account_id=model.account_id,
            counter_account_id=model.counter_account_id,
            category_id=model.category_id,
        )

    @staticmethod
    def to_model(entity: Movement) -> MovementModel:
        return MovementModel(
            id=entity.id,
            type=entity.type,
            amount_cents=to_cents(entity.amount),
            currency=entity.currency,
            description=entity.description,
            occurred_at=entity.occurred_at,
            account_id=entity.account_id,
            counter_account_id=entity.counter_account_id,
            category_id=entity.category_id,
        )
