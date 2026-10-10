from typing import TYPE_CHECKING

from uuid import UUID, uuid4

from sqlalchemy import Boolean, ForeignKey, String, Uuid, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.persistence.base import Base
from app.infrastructure.persistence.models.mixins import TimestampMixin


if TYPE_CHECKING:
    from app.infrastructure.persistence.models.finance.movement import Movement


class Category(TimestampMixin, Base):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_categories_user_name"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    movements: Mapped[list["Movement"]] = relationship(back_populates="category")

    def __repr__(self) -> str:
        return f"<Category {self.id} {self.name}>"
