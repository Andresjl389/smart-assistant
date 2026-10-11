from datetime import UTC, date, datetime, timedelta, timezone

import pytest

from app.domain.entities.work import WorkPreferences, WorkSession, WorkWeek


BOGOTA = timezone(timedelta(hours=-5))
PREFERENCES = WorkPreferences(
    weekly_target_minutes=42 * 60,
    timezone="America/Bogota",
    work_days=(1, 2, 3, 4, 5),
)


def at(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 10, day, hour, minute, tzinfo=BOGOTA)


def closed(day: int, start: int, end: int, break_minutes: int = 0) -> WorkSession:
    return WorkSession(started_at=at(day, start)).close(at(day, end), break_minutes)


def test_close_discounts_break():
    session = closed(5, 8, 17, break_minutes=60)

    assert session.duration_minutes == 540
    assert session.minutes == 480
    assert session.hours == 8.0


@pytest.mark.parametrize(
    ("start", "end", "break_minutes", "message"),
    [
        (at(5, 10), at(5, 9), 0, "terminar antes"),
        (at(5, 8), at(6, 9), 0, "24 horas"),
        (at(5, 8), at(5, 9), 60, "descanso"),
    ],
)
def test_reschedule_rejects_invalid_periods(start, end, break_minutes, message):
    with pytest.raises(ValueError, match=message):
        WorkSession(started_at=start).reschedule(ended_at=end, break_minutes=break_minutes)


def test_close_within_the_same_minute_counts_zero():
    session = WorkSession(started_at=at(5, 8)).close(at(5, 8) + timedelta(seconds=20))

    assert session.minutes == 0


def test_reschedule_keeps_unchanged_fields():
    session = closed(5, 8, 17, break_minutes=60)

    session.reschedule(ended_at=at(5, 18))

    assert session.started_at == at(5, 8)
    assert session.break_minutes == 60
    assert session.minutes == 540


def test_open_session_counts_until_now_capped_at_24_hours():
    session = WorkSession(started_at=at(5, 8), break_minutes=30)

    assert session.worked_minutes(at(5, 12)) == 210
    assert session.worked_minutes(at(8, 8)) == 24 * 60 - 30


def test_week_totals_and_remaining_quota():
    sessions = [closed(5, 8, 17, 60), closed(6, 8, 12), closed(10, 9, 11)]
    now = at(7, 7).astimezone(UTC)

    week = WorkWeek.build(date(2026, 10, 7), sessions, PREFERENCES, now)

    assert (week.week_start, week.week_end) == (date(2026, 10, 5), date(2026, 10, 11))
    assert week.worked_minutes == 480 + 240 + 120
    assert week.remaining_minutes == 42 * 60 - 840
    assert week.overtime_minutes == 0
    assert week.progress_percent == 33.3
    # Miercoles, jueves y viernes siguen disponibles.
    assert week.remaining_work_days == 3
    assert week.daily_minutes_needed == 560

    monday, tuesday, *_, saturday, _sunday = week.days
    assert monday.difference_minutes == 480 - 504
    assert tuesday.first_started_at == at(6, 8)
    assert tuesday.last_ended_at == at(6, 12)
    assert saturday.is_work_day is False
    assert saturday.worked_minutes == 120


def test_week_reports_overtime():
    sessions = [closed(day, 7, 17) for day in range(5, 10)]

    week = WorkWeek.build(date(2026, 10, 5), sessions, PREFERENCES, at(12, 8))

    assert week.is_completed
    assert week.overtime_minutes == 5 * 600 - 42 * 60
    assert week.daily_minutes_needed == 0


def test_week_uses_local_day_for_late_sessions():
    # Domingo 11 a las 21:00 en Bogota ya es lunes 12 en UTC.
    sessions = [WorkSession(started_at=at(11, 21)).close(at(11, 23))]

    week = WorkWeek.build(date(2026, 10, 11), sessions, PREFERENCES, at(12, 8))

    assert week.days[-1].worked_minutes == 120

    since, until = WorkWeek.bounds(date(2026, 10, 11), PREFERENCES)
    assert since == at(5, 0)
    assert until == at(12, 0)
