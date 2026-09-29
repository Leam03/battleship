from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from battleship.domain.board import ShotResult
from battleship.domain.play import Winner
from battleship.domain.state import Status, Turn

SCHEMA_REVISION = "0002"


class Base(DeclarativeBase):
    pass


class GameSession(Base):
    __tablename__ = "game_sessions"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'closed')", name="ck_game_status"),
        CheckConstraint("turn IN ('unknown', 'self', 'opponent')", name="ck_game_turn"),
        CheckConstraint("sequence >= 0", name="ck_game_sequence"),
        CheckConstraint(
            "pending_shot IS NULL OR (turn = 'self' AND pending_shot ~ '^[A-J](10|[1-9])$')",
            name="ck_game_pending",
        ),
        CheckConstraint("(status = 'closed') = (closed_at IS NOT NULL)", name="ck_game_closed_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    status: Mapped[Status] = mapped_column(String(8), default="active")
    turn: Mapped[Turn] = mapped_column(String(8), default="unknown")
    fleet: Mapped[list[list[str]]] = mapped_column(JSONB)
    pending_shot: Mapped[str | None] = mapped_column(String(3))
    sequence: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Shot(Base):
    __tablename__ = "shots"
    __table_args__ = (
        UniqueConstraint("session_id", "direction", "coordinate", name="uq_shot_cell"),
        UniqueConstraint("session_id", "sequence", name="uq_shot_sequence"),
        CheckConstraint("direction IN ('incoming', 'outgoing')", name="ck_shot_direction"),
        CheckConstraint("coordinate ~ '^[A-J](10|[1-9])$'", name="ck_shot_coordinate"),
        CheckConstraint("result IN ('miss', 'hit', 'killed')", name="ck_shot_result"),
        CheckConstraint("result IS NOT NULL OR direction = 'outgoing'", name="ck_shot_pending"),
        CheckConstraint("sequence > 0", name="ck_shot_sequence"),
        Index(
            "uq_shot_pending",
            "session_id",
            unique=True,
            postgresql_where=text("direction = 'outgoing' AND result IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    session_id: Mapped[UUID] = mapped_column(ForeignKey("game_sessions.id", ondelete="CASCADE"))
    sequence: Mapped[int]
    direction: Mapped[str] = mapped_column(String(8))
    coordinate: Mapped[str] = mapped_column(String(3))
    result: Mapped[ShotResult | None] = mapped_column(String(6))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BrowserGame(Base):
    __tablename__ = "browser_games"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'closed')", name="ck_browser_status"),
        CheckConstraint("winner IN ('player', 'bot')", name="ck_browser_winner"),
        CheckConstraint("winner IS NULL OR status = 'closed'", name="ck_browser_finished"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    status: Mapped[Status] = mapped_column(String(8), default="active")
    winner: Mapped[Winner | None] = mapped_column(String(6))
    player_fleet: Mapped[list[list[str]]] = mapped_column(JSONB)
    bot_fleet: Mapped[list[list[str]]] = mapped_column(JSONB)
    player_shots: Mapped[dict[str, ShotResult]] = mapped_column(JSONB, default=dict)
    bot_shots: Mapped[dict[str, ShotResult]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
