from app.domain.entities.work import WorkPreferences, WorkSession
from app.infrastructure.persistence.models.work.work_preferences import (
    WorkPreferences as WorkPreferencesModel,
)
from app.infrastructure.persistence.models.work.work_session import (
    WorkSession as WorkSessionModel,
)


class WorkSessionMapper:

    @staticmethod
    def to_domain(model: WorkSessionModel) -> WorkSession:
        return WorkSession(
            id=model.id,
            started_at=model.started_at,
            ended_at=model.ended_at,
            minutes=model.minutes,
            break_minutes=model.break_minutes,
            note=model.note,
        )

    @staticmethod
    def to_model(entity: WorkSession) -> WorkSessionModel:
        return WorkSessionModel(
            id=entity.id,
            started_at=entity.started_at,
            ended_at=entity.ended_at,
            minutes=entity.minutes,
            break_minutes=entity.break_minutes,
            note=entity.note,
        )


class WorkPreferencesMapper:

    @staticmethod
    def to_domain(model: WorkPreferencesModel) -> WorkPreferences:
        return WorkPreferences(
            weekly_target_minutes=model.weekly_target_minutes,
            timezone=model.timezone,
            work_days=tuple(int(day) for day in model.work_days.split(",")),
        )

    @staticmethod
    def serialize_work_days(work_days: tuple[int, ...]) -> str:
        return ",".join(str(day) for day in sorted(work_days))
