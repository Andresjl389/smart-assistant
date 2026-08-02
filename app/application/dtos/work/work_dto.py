from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.application.dtos.finance.finance_dto import require_timezone


class WorkSessionStartDTO(BaseModel):
    started_at: datetime | None = None
    note: str | None = Field(default=None, max_length=255)

    _check_timezone = field_validator("started_at")(require_timezone)


class WorkSessionStopDTO(BaseModel):
    ended_at: datetime | None = None

    _check_timezone = field_validator("ended_at")(require_timezone)


class WorkSessionDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    started_at: datetime
    ended_at: datetime | None
    minutes: int | None
    hours: float
    is_open: bool
    note: str | None


class WorkSummaryDTO(BaseModel):
    total_minutes: int
    total_hours: float
    sessions: int
