from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Enum,
    ForeignKey,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.value_objects.movement_type import MovementType
from app.infrastructure.persistence.base import Base
from app.infrastructure.persistence.models.mixins import TimestampMixin
from app.infrastructure.persistence.types import UtcDateTime


if TYPE_CHECKING:
    from app.infrastructure.persistence.models.finance.category import Category


class Movement(TimestampMixin, Base):
    __tablename__ = "movements"
    __table_args__ = (
        CheckConstraint("amount_cents > 0", name="amount_cents_positive"),
        CheckConstraint(
            "(type = 'TRANSFER' AND counter_account_id IS NOT NULL)"
            " OR (type <> 'TRANSFER' AND counter_account_id IS NULL)",
            name="transfer_requires_counter_account",
        ),
        CheckConstraint(
            "counter_account_id IS NULL OR counter_account_id <> account_id",
            name="counter_account_differs",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[MovementType] = mapped_column(
        Enum(MovementType, native_enum=False, name="movement_type", length=20),
        index=True,
    )
    amount_cents: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(3), default="COP")
    description: Mapped[str | None] = mapped_column(String(255))
    occurred_at: Mapped[datetime] = mapped_column(
        UtcDateTime,
        index=True,
    )
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        index=True,
    )
    counter_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        index=True,
    )
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"),
        index=True,
    )

    category: Mapped["Category | None"] = relationship(back_populates="movements")

    def __repr__(self) -> str:
        return f"<Movement {self.id} {self.type} {self.amount_cents} {self.currency}>"
