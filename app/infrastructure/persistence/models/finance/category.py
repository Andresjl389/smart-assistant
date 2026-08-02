from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.persistence.base import Base
from app.infrastructure.persistence.models.mixins import TimestampMixin


if TYPE_CHECKING:
    from app.infrastructure.persistence.models.finance.movement import Movement


class Category(TimestampMixin, Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    movements: Mapped[list["Movement"]] = relationship(back_populates="category")

    def __repr__(self) -> str:
        return f"<Category {self.id} {self.name}>"
