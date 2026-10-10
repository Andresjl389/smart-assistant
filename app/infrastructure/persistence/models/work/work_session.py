from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import Base
from app.infrastructure.persistence.models.mixins import TimestampMixin, utcnow
from app.infrastructure.persistence.types import UtcDateTime


class WorkSession(TimestampMixin, Base):
    __tablename__ = "work_sessions"
    __table_args__ = (
        CheckConstraint(
            "ended_at IS NULL OR ended_at > started_at",
            name="ended_after_started",
        ),
        CheckConstraint(
            "minutes IS NULL OR minutes >= 0",
            name="minutes_not_negative",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    started_at: Mapped[datetime] = mapped_column(
        UtcDateTime,
        default=utcnow,
        index=True,
    )
    ended_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    minutes: Mapped[int | None] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(String(255))

    def __repr__(self) -> str:
        return f"<WorkSession {self.id} {self.started_at} {self.minutes}min>"
