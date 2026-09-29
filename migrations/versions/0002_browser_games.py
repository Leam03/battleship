"""Store games played in the browser."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "browser_games",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("status", sa.String(8), nullable=False),
        sa.Column("winner", sa.String(6)),
        sa.Column("player_fleet", postgresql.JSONB(), nullable=False),
        sa.Column("bot_fleet", postgresql.JSONB(), nullable=False),
        sa.Column("player_shots", postgresql.JSONB(), nullable=False),
        sa.Column("bot_shots", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("status IN ('active', 'closed')", name="ck_browser_status"),
        sa.CheckConstraint("winner IN ('player', 'bot')", name="ck_browser_winner"),
        sa.CheckConstraint("winner IS NULL OR status = 'closed'", name="ck_browser_finished"),
    )


def downgrade():
    op.drop_table("browser_games")
