from app.domain.entities.work import WorkSession
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
            note=model.note,
        )

    @staticmethod
    def to_model(entity: WorkSession) -> WorkSessionModel:
        return WorkSessionModel(
            id=entity.id,
            started_at=entity.started_at,
            ended_at=entity.ended_at,
            minutes=entity.minutes,
            note=entity.note,
        )
