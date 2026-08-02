from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.domain.value_objects.account_type import AccountType
from app.domain.value_objects.movement_type import MovementType


@dataclass(slots=True)
class Account:
    name: str
    type: AccountType = AccountType.BANK
    currency: str = "COP"
    initial_balance: Decimal = Decimal(0)
    is_active: bool = True
    id: int | None = None


@dataclass(slots=True)
class AccountBalance:
    account: Account
    balance: Decimal


@dataclass(slots=True)
class Category:
    name: str
    is_active: bool = True
    id: int | None = None


@dataclass(slots=True)
class Movement:
    type: MovementType
    amount: Decimal
    occurred_at: datetime
    account_id: int
    counter_account_id: int | None = None
    currency: str = "COP"
    description: str | None = None
    category_id: int | None = None
    id: int | None = None

    @property
    def is_transfer(self) -> bool:
        return self.type is MovementType.TRANSFER

    @property
    def is_expense(self) -> bool:
        return self.type is MovementType.EXPENSE

    @property
    def signed_amount(self) -> Decimal:
        """Efecto sobre la cuenta de origen. Una transferencia sale de ella."""
        if self.type is MovementType.INCOME:
            return self.amount

        return -self.amount


@dataclass(slots=True)
class MovementSummary:
    income: Decimal = Decimal(0)
    expense: Decimal = Decimal(0)

    @property
    def balance(self) -> Decimal:
        return self.income - self.expense
