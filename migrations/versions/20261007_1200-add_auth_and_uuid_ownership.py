"""add cookie authentication, per-user ownership, and UUID identifiers

Revision ID: 9f6a1b2c3d4e
Revises: b328d4375cde
"""
from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

from app.infrastructure.persistence.models import Base
from app.infrastructure.persistence.models.auth import User

revision = "9f6a1b2c3d4e"
down_revision = "b328d4375cde"
branch_labels = None
depends_on = None


def _rows(conn, table):
    return [dict(row._mapping) for row in conn.execute(sa.text(f'SELECT * FROM "{table}"'))]


def _normalize_dates(row, fields):
    for field in fields:
        value = row.get(field)
        if isinstance(value, str):
            value = datetime.fromisoformat(value)
        if isinstance(value, datetime) and value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        row[field] = value
    return row


def upgrade() -> None:
    conn = op.get_bind()
    old = {name: _rows(conn, name) for name in ("accounts", "categories", "movements", "work_sessions")}
    owner_id = uuid4()
    account_ids = {row["id"]: uuid4() for row in old["accounts"]}
    category_ids = {row["id"]: uuid4() for row in old["categories"]}
    movement_ids = {row["id"]: uuid4() for row in old["movements"]}
    work_ids = {row["id"]: uuid4() for row in old["work_sessions"]}

    # Remove the old integer-keyed tables, then create their UUID schema.
    for name in ("movements", "accounts", "categories", "work_sessions"):
        op.drop_table(name)
    Base.metadata.create_all(bind=conn)

    now = datetime.now(UTC)
    conn.execute(User.__table__.insert().values(
        id=owner_id,
        email="legacy-data@internal.invalid",
        password_hash="!legacy-account-cannot-authenticate!",
        created_at=now,
        updated_at=now,
    ))

    account_table = Base.metadata.tables["accounts"]
    category_table = Base.metadata.tables["categories"]
    movement_table = Base.metadata.tables["movements"]
    work_table = Base.metadata.tables["work_sessions"]
    for row in old["accounts"]:
        _normalize_dates(row, ("created_at", "updated_at"))
        row.update(id=account_ids[row["id"]], user_id=owner_id)
        conn.execute(account_table.insert().values(**row))
    for row in old["categories"]:
        _normalize_dates(row, ("created_at", "updated_at"))
        row.update(id=category_ids[row["id"]], user_id=owner_id)
        conn.execute(category_table.insert().values(**row))
    for row in old["movements"]:
        _normalize_dates(row, ("occurred_at", "created_at", "updated_at"))
        row["id"] = movement_ids[row["id"]]
        row["account_id"] = account_ids[row["account_id"]]
        row["counter_account_id"] = account_ids.get(row["counter_account_id"])
        row["category_id"] = category_ids.get(row["category_id"])
        row["user_id"] = owner_id
        conn.execute(movement_table.insert().values(**row))
    for row in old["work_sessions"]:
        _normalize_dates(row, ("started_at", "ended_at", "created_at", "updated_at"))
        row.update(id=work_ids[row["id"]], user_id=owner_id)
        conn.execute(work_table.insert().values(**row))


def downgrade() -> None:
    raise RuntimeError("No es seguro volver a IDs numéricos: la migración UUID no tiene reversión sin pérdida.")
