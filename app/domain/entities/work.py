from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from typing import Self
from uuid import UUID
from zoneinfo import ZoneInfo


SECONDS_PER_MINUTE = 60
MINUTES_PER_HOUR = 60
MAX_SESSION_HOURS = 24
DAYS_PER_WEEK = 7


def to_hours(minutes: int) -> float:
    return round(minutes / MINUTES_PER_HOUR, 2)


def minutes_between(start: datetime, end: datetime) -> int:
    return int((end - start).total_seconds() // SECONDS_PER_MINUTE)


@dataclass(slots=True)
class WorkSession:
    started_at: datetime
    ended_at: datetime | None = None
    # Minutos netos trabajados: duracion de la jornada menos el descanso.
    minutes: int | None = None
    break_minutes: int = 0
    note: str | None = None
    id: UUID | None = None

    @property
    def is_open(self) -> bool:
        return self.ended_at is None

    @property
    def hours(self) -> float:
        return to_hours(self.minutes or 0)

    @property
    def duration_minutes(self) -> int | None:
        if self.ended_at is None:
            return None

        return minutes_between(self.started_at, self.ended_at)

    def worked_minutes(self, now: datetime | None = None) -> int:
        """Minutos netos; si la jornada sigue abierta, los cuenta hasta `now`.

        Una jornada abierta que se olvido cerrar no suma mas del maximo
        permitido, para no inflar los totales de la semana.
        """
        if self.minutes is not None:
            return self.minutes

        elapsed = min(
            minutes_between(self.started_at, now or datetime.now(UTC)),
            MAX_SESSION_HOURS * MINUTES_PER_HOUR,
        )

        return max(elapsed - self.break_minutes, 0)

    def close(
        self,
        ended_at: datetime | None = None,
        break_minutes: int | None = None,
    ) -> Self:
        return self.reschedule(
            ended_at=ended_at or datetime.now(UTC),
            break_minutes=break_minutes,
        )

    def reschedule(
        self,
        started_at: datetime | None = None,
        ended_at: datetime | None = None,
        break_minutes: int | None = None,
    ) -> Self:
        started_at = started_at or self.started_at
        ended_at = ended_at or self.ended_at
        break_minutes = self.break_minutes if break_minutes is None else break_minutes

        if break_minutes < 0:
            raise ValueError("El descanso no puede ser negativo.")

        minutes = None

        if ended_at is not None:
            if ended_at <= started_at:
                raise ValueError("La jornada no puede terminar antes de empezar.")

            duration = minutes_between(started_at, ended_at)

            if duration > MAX_SESSION_HOURS * MINUTES_PER_HOUR:
                raise ValueError(
                    f"Una jornada no puede durar más de {MAX_SESSION_HOURS} horas. "
                    "Revisa la fecha de ingreso y de salida.",
                )

            if break_minutes and break_minutes >= duration:
                raise ValueError(
                    "El descanso no puede ser igual o mayor que la duración "
                    "de la jornada.",
                )

            minutes = duration - break_minutes

        self.started_at = started_at
        self.ended_at = ended_at
        self.break_minutes = break_minutes
        self.minutes = minutes

        return self


@dataclass(slots=True)
class WorkPreferences:
    weekly_target_minutes: int
    timezone: str
    # Dias laborales en formato ISO: 1 = lunes ... 7 = domingo.
    work_days: tuple[int, ...]

    @property
    def tzinfo(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    @property
    def weekly_target_hours(self) -> float:
        return to_hours(self.weekly_target_minutes)

    @property
    def daily_target_minutes(self) -> int:
        return self.weekly_target_minutes // len(self.work_days)

    def is_work_day(self, day: date) -> bool:
        return day.isoweekday() in self.work_days


@dataclass(slots=True)
class WorkDay:
    day: date
    is_work_day: bool
    target_minutes: int
    worked_minutes: int = 0
    sessions: int = 0
    first_started_at: datetime | None = None
    last_ended_at: datetime | None = None

    @property
    def worked_hours(self) -> float:
        return to_hours(self.worked_minutes)

    @property
    def difference_minutes(self) -> int:
        """Positivo si se trabajo de mas ese dia, negativo si falto."""
        return self.worked_minutes - self.target_minutes


@dataclass(slots=True)
class WorkWeek:
    week_start: date
    week_end: date
    timezone: str
    target_minutes: int
    worked_minutes: int
    sessions: int
    has_open_session: bool
    remaining_work_days: int
    days: list[WorkDay] = field(default_factory=list)

    @property
    def remaining_minutes(self) -> int:
        return max(self.target_minutes - self.worked_minutes, 0)

    @property
    def overtime_minutes(self) -> int:
        return max(self.worked_minutes - self.target_minutes, 0)

    @property
    def is_completed(self) -> bool:
        return self.worked_minutes >= self.target_minutes

    @property
    def progress_percent(self) -> float:
        return round(self.worked_minutes * 100 / self.target_minutes, 1)

    @property
    def daily_minutes_needed(self) -> int | None:
        """Promedio diario para completar la cuota en los dias laborales que quedan."""
        if self.is_completed:
            return 0

        if self.remaining_work_days == 0:
            return None

        return -(-self.remaining_minutes // self.remaining_work_days)

    @property
    def target_hours(self) -> float:
        return to_hours(self.target_minutes)

    @property
    def worked_hours(self) -> float:
        return to_hours(self.worked_minutes)

    @property
    def remaining_hours(self) -> float:
        return to_hours(self.remaining_minutes)

    @property
    def overtime_hours(self) -> float:
        return to_hours(self.overtime_minutes)

    @staticmethod
    def bounds(reference: date, preferences: WorkPreferences) -> tuple[datetime, datetime]:
        """Inicio (incluido) y fin (excluido) de la semana, lunes a lunes, en UTC."""
        monday = reference - timedelta(days=reference.weekday())
        start = datetime.combine(monday, time.min, tzinfo=preferences.tzinfo)
        end = datetime.combine(
            monday + timedelta(days=DAYS_PER_WEEK),
            time.min,
            tzinfo=preferences.tzinfo,
        )

        return start.astimezone(UTC), end.astimezone(UTC)

    @classmethod
    def build(
        cls,
        reference: date,
        sessions: list[WorkSession],
        preferences: WorkPreferences,
        now: datetime | None = None,
    ) -> Self:
        """Arma el resumen de la semana que contiene `reference`.

        Cada jornada cuenta para el dia (hora local) en que empezo, aunque
        termine despues de medianoche.
        """
        now = now or datetime.now(UTC)
        tz = preferences.tzinfo
        today = now.astimezone(tz).date()
        monday = reference - timedelta(days=reference.weekday())
        week = [monday + timedelta(days=offset) for offset in range(DAYS_PER_WEEK)]

        days = {
            day: WorkDay(
                day=day,
                is_work_day=preferences.is_work_day(day),
                target_minutes=(
                    preferences.daily_target_minutes
                    if preferences.is_work_day(day)
                    else 0
                ),
            )
            for day in week
        }

        for session in sessions:
            work_day = days.get(session.started_at.astimezone(tz).date())

            if work_day is None:
                continue

            work_day.worked_minutes += session.worked_minutes(now)
            work_day.sessions += 1

            started_at = session.started_at.astimezone(tz)

            if work_day.first_started_at is None or started_at < work_day.first_started_at:
                work_day.first_started_at = started_at

            if session.ended_at is not None:
                ended_at = session.ended_at.astimezone(tz)

                if work_day.last_ended_at is None or ended_at > work_day.last_ended_at:
                    work_day.last_ended_at = ended_at

        return cls(
            week_start=week[0],
            week_end=week[-1],
            timezone=preferences.timezone,
            target_minutes=preferences.weekly_target_minutes,
            worked_minutes=sum(day.worked_minutes for day in days.values()),
            sessions=sum(day.sessions for day in days.values()),
            has_open_session=any(session.is_open for session in sessions),
            remaining_work_days=sum(
                1 for day in week if day >= today and preferences.is_work_day(day)
            ),
            days=list(days.values()),
        )
