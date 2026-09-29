from datetime import UTC, datetime
from random import Random
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from battleship.db import queries
from battleship.db.models import GameSession
from battleship.domain.board import ShotResult, resolve_shot
from battleship.domain.fleet import generate_fleet
from battleship.domain.state import GameState
from battleship.domain.targeting import choose_shot


def read_state(game: GameSession) -> GameState:
    return GameState(game.status, game.turn, game.pending_shot)


def write_state(game: GameSession, state: GameState) -> None:
    game.status, game.turn, game.pending_shot = state.status, state.turn, state.pending_shot


async def create_game(db: AsyncSession, rng: Random) -> GameSession:
    async with db.begin():
        game = GameSession(fleet=[list(ship) for ship in generate_fleet(rng)])
        db.add(game)
        await db.flush()
    return game


async def make_shot(db: AsyncSession, session_id: UUID, rng: Random) -> str:
    async with db.begin():
        game = await queries.get_game_for_update(db, session_id)
        state = read_state(game)
        state.require_shot()
        shots = await queries.list_shots(db, session_id, "outgoing")
        history = {shot.coordinate: shot.result for shot in shots if shot.result is not None}
        coordinate = choose_shot(history, rng)
        state.request_shot(coordinate)
        queries.add_shot(db, game, "outgoing", coordinate, None)
        write_state(game, state)
    return coordinate


async def accept_shot_result(db: AsyncSession, session_id: UUID, result: ShotResult) -> None:
    async with db.begin():
        game = await queries.get_game_for_update(db, session_id)
        state = read_state(game)
        coordinate = state.accept_result(result)
        await queries.complete_pending_shot(db, game, coordinate, result)
        write_state(game, state)


async def receive_opponent_shot(db: AsyncSession, session_id: UUID, coordinate: str) -> ShotResult:
    async with db.begin():
        game = await queries.get_game_for_update(db, session_id)
        state = read_state(game)
        state.require_active()
        shots = await queries.list_shots(db, session_id, "incoming")
        history = {shot.coordinate: shot.result for shot in shots if shot.result is not None}
        result = resolve_shot(tuple(tuple(ship) for ship in game.fleet), history, coordinate)
        state.receive_shot(result)
        queries.add_shot(db, game, "incoming", coordinate, result)
        write_state(game, state)
    return result


async def close_game(db: AsyncSession, session_id: UUID) -> None:
    async with db.begin():
        game = await queries.get_game_for_update(db, session_id)
        state = read_state(game)
        state.close()
        game.closed_at = datetime.now(UTC)
        write_state(game, state)
