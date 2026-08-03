from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.value_objects.account_type import AccountType
from app.domain.value_objects.movement_type import MovementType


def require_timezone(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        raise ValueError(
            "La fecha debe incluir zona horaria. "
            "Ejemplo: 2026-08-02T10:30:00-05:00",
        )

    return value


class AccountCreateDTO(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    type: AccountType = AccountType.BANK
    currency: str = Field(default="COP", min_length=3, max_length=3)
    initial_balance: Decimal = Field(default=Decimal(0), decimal_places=2)
    is_active: bool = True


class AccountDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: AccountType
    currency: str
    initial_balance: Decimal
    is_active: bool


class AccountBalanceDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    account: AccountDTO
    balance: Decimal


class CategoryCreateDTO(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    is_active: bool = True


class CategoryDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    is_active: bool


class MovementCreateDTO(BaseModel):
    type: MovementType
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    account_id: int
    occurred_at: datetime | None = None
    description: str | None = Field(default=None, max_length=255)
    category_id: int | None = None

    _check_timezone = field_validator("occurred_at")(require_timezone)

    @field_validator("type")
    @classmethod
    def reject_transfer(cls, value: MovementType) -> MovementType:
        if value is MovementType.TRANSFER:
            raise ValueError(
                "Las transferencias se registran en POST /finance/transfers.",
            )

        return value


class TransferCreateDTO(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    from_account_id: int
    to_account_id: int
    occurred_at: datetime | None = None
    description: str | None = Field(default=None, max_length=255)

    _check_timezone = field_validator("occurred_at")(require_timezone)


class MovementDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: MovementType
    amount: Decimal
    signed_amount: Decimal
    currency: str
    description: str | None
    occurred_at: datetime
    account_id: int
    counter_account_id: int | None
    category_id: int | None


class MovementSummaryDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    income: Decimal
    expense: Decimal
    balance: Decimal
