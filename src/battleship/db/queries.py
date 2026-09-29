from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from battleship.db.models import GameSession, Shot
from battleship.domain.board import ShotResult
from battleship.domain.errors import SessionNotFound


async def get_game_for_update(db: AsyncSession, session_id: UUID) -> GameSession:
    game = await db.scalar(
        select(GameSession).where(GameSession.id == session_id).with_for_update()
    )
    if game is None:
        raise SessionNotFound("Session not found")
    return game


async def list_shots(db: AsyncSession, session_id: UUID, direction: str) -> list[Shot]:
    rows = await db.scalars(
        select(Shot)
        .where(Shot.session_id == session_id, Shot.direction == direction)
        .order_by(Shot.sequence)
    )
    return list(rows)


def add_shot(
    db: AsyncSession,
    game: GameSession,
    direction: str,
    coordinate: str,
    result: ShotResult | None,
) -> None:
    game.sequence += 1
    db.add(
        Shot(
            session_id=game.id,
            sequence=game.sequence,
            direction=direction,
            coordinate=coordinate,
            result=result,
        )
    )


async def complete_pending_shot(
    db: AsyncSession, game: GameSession, coordinate: str, result: ShotResult
) -> None:
    shot = (
        await db.scalars(
            select(Shot).where(
                Shot.session_id == game.id,
                Shot.direction == "outgoing",
                Shot.coordinate == coordinate,
                Shot.result.is_(None),
            )
        )
    ).one()
    shot.result = result
