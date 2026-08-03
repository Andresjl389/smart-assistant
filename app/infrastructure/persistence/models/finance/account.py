from sqlalchemy import BigInteger, Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.value_objects.account_type import AccountType
from app.infrastructure.persistence.base import Base
from app.infrastructure.persistence.models.mixins import TimestampMixin


class Account(TimestampMixin, Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    type: Mapped[AccountType] = mapped_column(
        Enum(AccountType, native_enum=False, name="account_type", length=20),
    )
    currency: Mapped[str] = mapped_column(String(3), default="COP")
    initial_balance_cents: Mapped[int] = mapped_column(BigInteger, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def __repr__(self) -> str:
        return f"<Account {self.id} {self.name} {self.currency}>"
