from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Self


SECONDS_PER_MINUTE = 60
MINUTES_PER_HOUR = 60


@dataclass(slots=True)
class WorkSession:
    started_at: datetime
    ended_at: datetime | None = None
    minutes: int | None = None
    note: str | None = None
    id: int | None = None

    @property
    def is_open(self) -> bool:
        return self.ended_at is None

    @property
    def hours(self) -> float:
        return round((self.minutes or 0) / MINUTES_PER_HOUR, 2)

    def close(self, ended_at: datetime | None = None) -> Self:
        closed_at = ended_at or datetime.now(UTC)

        if closed_at <= self.started_at:
            raise ValueError("La jornada no puede terminar antes de empezar.")

        self.ended_at = closed_at
        elapsed = closed_at - self.started_at
        self.minutes = int(elapsed.total_seconds() // SECONDS_PER_MINUTE)

        return self
