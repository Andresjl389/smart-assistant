"""add break minutes to work sessions and per-user work preferences

Revision ID: c4e8a2f17b90
Revises: 9f6a1b2c3d4e
"""
import sqlalchemy as sa
from alembic import op

revision = "c4e8a2f17b90"
down_revision = "9f6a1b2c3d4e"
branch_labels = None
depends_on = None


# La migracion 9f6a1b2c3d4e recrea las tablas con Base.metadata.create_all,
# que usa los modelos actuales: en una base nueva la columna y la tabla de
# esta migracion ya pueden existir, asi que cada paso verifica antes de crear.


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    work_columns = {column["name"] for column in inspector.get_columns("work_sessions")}

    if "break_minutes" not in work_columns:
        with op.batch_alter_table("work_sessions", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("break_minutes", sa.Integer(), server_default="0", nullable=False),
            )
            batch_op.create_check_constraint(
                op.f("ck_work_sessions_break_minutes_not_negative"),
                "break_minutes >= 0",
            )

    if not inspector.has_table("work_preferences"):
        op.create_table(
            "work_preferences",
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("weekly_target_minutes", sa.Integer(), nullable=False),
            sa.Column("timezone", sa.String(length=64), nullable=False),
            sa.Column("work_days", sa.String(length=20), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint(
                "weekly_target_minutes > 0",
                name=op.f("ck_work_preferences_weekly_target_minutes_positive"),
            ),
            sa.ForeignKeyConstraint(
                ["user_id"],
                ["users.id"],
                name=op.f("fk_work_preferences_user_id_users"),
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("user_id", name=op.f("pk_work_preferences")),
        )


def downgrade() -> None:
    op.drop_table("work_preferences")

    with op.batch_alter_table("work_sessions", schema=None) as batch_op:
        batch_op.drop_constraint(
            op.f("ck_work_sessions_break_minutes_not_negative"),
            type_="check",
        )
        batch_op.drop_column("break_minutes")
