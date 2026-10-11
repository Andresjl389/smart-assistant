from datetime import date, datetime
from typing import Annotated, Any
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.application.dtos.finance.finance_dto import require_timezone
from app.domain.entities.work import MAX_SESSION_HOURS, MINUTES_PER_HOUR


MAX_BREAK_MINUTES = MAX_SESSION_HOURS * MINUTES_PER_HOUR

# Las entradas rechazan campos desconocidos: un `startedAt` mal escrito
# devuelve 422 en vez de ignorarse y registrar la hora actual.
INPUT_CONFIG = ConfigDict(extra="forbid")

TIMEZONE_HINT = "Debe incluir zona horaria, p. ej. `-05:00` o `Z`."

IsoWeekday = Annotated[
    int,
    Field(ge=1, le=7, description="Día ISO: 1 = lunes … 7 = domingo."),
]


def require_known_timezone(value: str | None) -> str | None:
    if value is None:
        return value

    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise ValueError(
            f"Zona horaria desconocida: {value}. Ejemplo: America/Bogota",
        ) from error

    return value


def normalize_work_days(value: list[int] | None) -> list[int] | None:
    if value is None:
        return value

    return sorted(set(value))


def documented_field(defaults: dict[str, Any], overrides: dict[str, Any]) -> Any:
    return Field(**(defaults | overrides))


def started_at_field(**overrides: Any) -> Any:
    return documented_field(
        {
            "description": f"Hora de ingreso. {TIMEZONE_HINT}",
            "examples": ["2026-10-05T08:00:00-05:00"],
        },
        overrides,
    )


def ended_at_field(**overrides: Any) -> Any:
    return documented_field(
        {
            "description": (
                f"Hora de salida; debe ser posterior al ingreso y la jornada no "
                f"puede superar {MAX_SESSION_HOURS} horas. {TIMEZONE_HINT}"
            ),
            "examples": ["2026-10-05T17:00:00-05:00"],
        },
        overrides,
    )


def break_minutes_field(**overrides: Any) -> Any:
    return documented_field(
        {
            "ge": 0,
            "le": MAX_BREAK_MINUTES,
            "description": (
                "Minutos de descanso (almuerzo, pausas) que se descuentan del "
                "tiempo trabajado. Debe ser menor que la duración de la jornada."
            ),
            "examples": [60],
        },
        overrides,
    )


def note_field(**overrides: Any) -> Any:
    return documented_field(
        {
            "max_length": 255,
            "description": "Nota libre sobre la jornada.",
            "examples": ["Oficina"],
        },
        overrides,
    )


# --- Entradas -----------------------------------------------------------------


class WorkSessionStartDTO(BaseModel):
    """Marca la entrada. Todo es opcional: sin cuerpo se usa la hora actual."""

    model_config = INPUT_CONFIG

    started_at: datetime | None = started_at_field(
        default=None,
        description=f"Hora de ingreso; si se omite, la hora actual. {TIMEZONE_HINT}",
    )
    note: str | None = note_field(default=None)

    _check_timezone = field_validator("started_at")(require_timezone)


class WorkSessionStopDTO(BaseModel):
    """Marca la salida de la jornada abierta. Todo es opcional."""

    model_config = INPUT_CONFIG

    ended_at: datetime | None = ended_at_field(
        default=None,
        description=f"Hora de salida; si se omite, la hora actual. {TIMEZONE_HINT}",
    )
    break_minutes: int | None = break_minutes_field(
        default=None,
        description=(
            "Minutos de descanso a descontar. Si se omite, se conserva el "
            "valor que ya tenía la jornada (0 por defecto)."
        ),
    )

    _check_timezone = field_validator("ended_at")(require_timezone)


class WorkSessionCreateDTO(BaseModel):
    """Registro manual de una jornada ya terminada, con hora de ingreso y salida."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "started_at": "2026-10-05T08:00:00-05:00",
                    "ended_at": "2026-10-05T17:00:00-05:00",
                    "break_minutes": 60,
                    "note": "Oficina",
                },
            ],
        },
    )

    started_at: datetime = started_at_field()
    ended_at: datetime = ended_at_field()
    break_minutes: int = break_minutes_field(default=0)
    note: str | None = note_field(default=None)

    _check_timezone = field_validator("started_at", "ended_at")(require_timezone)


class WorkSessionUpdateDTO(BaseModel):
    """Corrige una jornada. Solo se modifican los campos enviados (al menos uno).

    Enviar `ended_at` a una jornada abierta la cierra. `note: null` borra la nota.
    """

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {"ended_at": "2026-10-05T18:00:00-05:00", "break_minutes": 45},
            ],
        },
    )

    started_at: datetime | None = started_at_field(default=None)
    ended_at: datetime | None = ended_at_field(default=None)
    break_minutes: int | None = break_minutes_field(default=None)
    note: str | None = note_field(default=None)

    _check_timezone = field_validator("started_at", "ended_at")(require_timezone)

    @model_validator(mode="after")
    def require_changes(self) -> "WorkSessionUpdateDTO":
        if not self.model_fields_set:
            raise ValueError("Envía al menos un campo para modificar.")

        return self


class WorkPreferencesUpdateDTO(BaseModel):
    """Cambia las preferencias de horas. Solo se modifican los campos enviados."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "weekly_target_hours": 42,
                    "timezone": "America/Bogota",
                    "work_days": [1, 2, 3, 4, 5],
                },
            ],
        },
    )

    weekly_target_hours: float | None = Field(
        default=None,
        gt=0,
        le=168,
        description="Cuota de horas a cumplir por semana.",
        examples=[42],
    )
    timezone: str | None = Field(
        default=None,
        max_length=64,
        description=(
            "Zona horaria IANA con la que se arman los días y las semanas."
        ),
        examples=["America/Bogota"],
    )
    work_days: list[IsoWeekday] | None = Field(
        default=None,
        min_length=1,
        max_length=7,
        description=(
            "Días laborales ISO (1 = lunes … 7 = domingo). La cuota semanal "
            "se reparte en partes iguales entre ellos."
        ),
        examples=[[1, 2, 3, 4, 5]],
    )

    _check_timezone = field_validator("timezone")(require_known_timezone)
    _normalize_days = field_validator("work_days")(normalize_work_days)

    @model_validator(mode="after")
    def require_changes(self) -> "WorkPreferencesUpdateDTO":
        if not self.model_fields_set:
            raise ValueError("Envía al menos un campo para modificar.")

        return self


# --- Respuestas ---------------------------------------------------------------


class WorkSessionDTO(BaseModel):
    """Una jornada de trabajo."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="Identificador de la jornada.")
    started_at: datetime = Field(description="Hora de ingreso (UTC).")
    ended_at: datetime | None = Field(
        description="Hora de salida (UTC); `null` si la jornada sigue abierta.",
    )
    duration_minutes: int | None = Field(
        description="Minutos entre ingreso y salida, sin descontar el descanso.",
        examples=[540],
    )
    break_minutes: int = Field(description="Minutos de descanso.", examples=[60])
    minutes: int | None = Field(
        description="Minutos netos trabajados (duración − descanso).",
        examples=[480],
    )
    hours: float = Field(description="`minutes` expresado en horas.", examples=[8.0])
    is_open: bool = Field(description="`true` si aún no se marcó la salida.")
    note: str | None = Field(description="Nota libre.")


class WorkSummaryDTO(BaseModel):
    """Totales de las jornadas cerradas en un periodo."""

    total_minutes: int = Field(description="Minutos netos trabajados.")
    total_hours: float = Field(description="`total_minutes` en horas.")
    sessions: int = Field(description="Cantidad de jornadas en el periodo.")


class WorkPreferencesDTO(BaseModel):
    """Preferencias de horas del usuario (o los valores por defecto)."""

    model_config = ConfigDict(from_attributes=True)

    weekly_target_minutes: int = Field(
        description="Cuota semanal en minutos.",
        examples=[2520],
    )
    weekly_target_hours: float = Field(
        description="Cuota semanal en horas.",
        examples=[42.0],
    )
    daily_target_minutes: int = Field(
        description="Meta por día laboral: cuota semanal / días laborales.",
        examples=[504],
    )
    timezone: str = Field(description="Zona horaria IANA.", examples=["America/Bogota"])
    work_days: list[int] = Field(
        description="Días laborales ISO (1 = lunes … 7 = domingo).",
        examples=[[1, 2, 3, 4, 5]],
    )


class WorkDayDTO(BaseModel):
    """Lo trabajado en un día de la semana (hora local)."""

    model_config = ConfigDict(from_attributes=True)

    day: date = Field(description="Fecha local.")
    is_work_day: bool = Field(description="Si es día laboral según las preferencias.")
    target_minutes: int = Field(
        description="Meta del día en minutos; 0 si no es día laboral.",
    )
    worked_minutes: int = Field(description="Minutos netos trabajados ese día.")
    worked_hours: float = Field(description="`worked_minutes` en horas.")
    difference_minutes: int = Field(
        description="`worked_minutes − target_minutes`: positivo si sobró, negativo si faltó.",
    )
    sessions: int = Field(description="Jornadas que empezaron ese día.")
    first_started_at: datetime | None = Field(
        description="Primera entrada del día, en la zona horaria del usuario.",
    )
    last_ended_at: datetime | None = Field(
        description="Última salida del día, en la zona horaria del usuario.",
    )


class WorkWeekDTO(BaseModel):
    """Avance de la semana (lunes a domingo) frente a la cuota semanal."""

    model_config = ConfigDict(from_attributes=True)

    week_start: date = Field(description="Lunes de la semana.")
    week_end: date = Field(description="Domingo de la semana.")
    timezone: str = Field(description="Zona horaria usada para armar los días.")
    target_minutes: int = Field(description="Cuota semanal en minutos.")
    target_hours: float = Field(description="Cuota semanal en horas.")
    worked_minutes: int = Field(
        description="Minutos netos trabajados; incluye la jornada abierta hasta ahora.",
    )
    worked_hours: float = Field(description="`worked_minutes` en horas.")
    remaining_minutes: int = Field(
        description="Minutos que faltan para la cuota; 0 si ya se cumplió.",
    )
    remaining_hours: float = Field(description="`remaining_minutes` en horas.")
    overtime_minutes: int = Field(description="Minutos por encima de la cuota.")
    overtime_hours: float = Field(description="`overtime_minutes` en horas.")
    progress_percent: float = Field(
        description="Avance frente a la cuota; puede pasar de 100.",
        examples=[32.1],
    )
    is_completed: bool = Field(description="`true` si ya se cumplió la cuota.")
    sessions: int = Field(description="Jornadas de la semana.")
    has_open_session: bool = Field(description="Si hay una jornada sin salida.")
    remaining_work_days: int = Field(
        description="Días laborales que quedan en la semana, contando hoy.",
    )
    daily_minutes_needed: int | None = Field(
        description=(
            "Minutos promedio por día laboral restante para cumplir la cuota. "
            "0 si ya se cumplió; `null` si no quedan días laborales."
        ),
    )
    days: list[WorkDayDTO] = Field(description="Detalle de lunes a domingo.")
