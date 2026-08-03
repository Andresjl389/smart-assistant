from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


class UtcDateTime(TypeDecorator):
    """Garantiza datetimes UTC con zona horaria en cualquier motor.

    SQLite no guarda el offset y devuelve datetimes naive; Postgres si lo
    conserva. Este tipo normaliza la lectura para que la aplicacion siempre
    reciba datetimes aware en UTC, sin importar la base de datos.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(
        self,
        value: datetime | None,
        dialect,
    ) -> datetime | None:
        if value is None:
            return None

        if value.tzinfo is None:
            raise ValueError(
                "Se requiere un datetime con zona horaria. "
                "Usa datetime.now(UTC) o adjunta tzinfo antes de guardar.",
            )

        return value.astimezone(UTC)

    def process_result_value(
        self,
        value: datetime | None,
        dialect,
    ) -> datetime | None:
        if value is None:
            return None

        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)

        return value.astimezone(UTC)
