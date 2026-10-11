from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import Base
from app.infrastructure.persistence.models.mixins import TimestampMixin


class WorkPreferences(TimestampMixin, Base):
    __tablename__ = "work_preferences"
    __table_args__ = (
        CheckConstraint(
            "weekly_target_minutes > 0",
            name="weekly_target_minutes_positive",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    weekly_target_minutes: Mapped[int] = mapped_column(Integer)
    timezone: Mapped[str] = mapped_column(String(64))
    # Dias ISO separados por coma: "1,2,3,4,5" = lunes a viernes.
    work_days: Mapped[str] = mapped_column(String(20))

    def __repr__(self) -> str:
        return f"<WorkPreferences {self.user_id} {self.weekly_target_minutes}min>"
