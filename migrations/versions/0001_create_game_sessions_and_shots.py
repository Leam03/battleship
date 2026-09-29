"""Create sessions and shot history."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "game_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(8), nullable=False),
        sa.Column("turn", sa.String(8), nullable=False),
        sa.Column("fleet", postgresql.JSONB(), nullable=False),
        sa.Column("pending_shot", sa.String(3)),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("status IN ('active', 'closed')", name="ck_game_status"),
        sa.CheckConstraint("turn IN ('unknown', 'self', 'opponent')", name="ck_game_turn"),
        sa.CheckConstraint("sequence >= 0", name="ck_game_sequence"),
        sa.CheckConstraint(
            "pending_shot IS NULL OR (turn = 'self' AND pending_shot ~ '^[A-J](10|[1-9])$')",
            name="ck_game_pending",
        ),
        sa.CheckConstraint(
            "(status = 'closed') = (closed_at IS NOT NULL)", name="ck_game_closed_at"
        ),
    )
    op.create_table(
        "shots",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "session_id",
            sa.Uuid(),
            sa.ForeignKey("game_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("direction", sa.String(8), nullable=False),
        sa.Column("coordinate", sa.String(3), nullable=False),
        sa.Column("result", sa.String(6)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("session_id", "direction", "coordinate", name="uq_shot_cell"),
        sa.UniqueConstraint("session_id", "sequence", name="uq_shot_sequence"),
        sa.CheckConstraint("direction IN ('incoming', 'outgoing')", name="ck_shot_direction"),
        sa.CheckConstraint("coordinate ~ '^[A-J](10|[1-9])$'", name="ck_shot_coordinate"),
        sa.CheckConstraint("result IN ('miss', 'hit', 'killed')", name="ck_shot_result"),
        sa.CheckConstraint("result IS NOT NULL OR direction = 'outgoing'", name="ck_shot_pending"),
        sa.CheckConstraint("sequence > 0", name="ck_shot_sequence"),
    )
    op.create_index(
        "uq_shot_pending",
        "shots",
        ["session_id"],
        unique=True,
        postgresql_where=sa.text("direction = 'outgoing' AND result IS NULL"),
    )


def downgrade():
    op.drop_table("shots")
    op.drop_table("game_sessions")
