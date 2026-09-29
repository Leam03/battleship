from random import Random
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from battleship.db.models import BrowserGame
from battleship.domain.errors import SessionClosed, SessionNotFound
from battleship.domain.fleet import Fleet, generate_fleet, validate_fleet
from battleship.domain.play import HumanGame


async def create_game(db: AsyncSession, fleet: Fleet, rng: Random) -> BrowserGame:
    validate_fleet(fleet)
    async with db.begin():
        game = BrowserGame(
            player_fleet=[list(ship) for ship in fleet],
            bot_fleet=[list(ship) for ship in generate_fleet(rng)],
        )
        db.add(game)
        await db.flush()
    return game


async def get_game(db: AsyncSession, game_id: UUID, *, lock: bool = False) -> BrowserGame:
    query = select(BrowserGame).where(BrowserGame.id == game_id)
    game = await db.scalar(query.with_for_update() if lock else query)
    if game is None:
        raise SessionNotFound("Game not found")
    return game


async def fire(db: AsyncSession, game_id: UUID, coordinate: str, rng: Random) -> BrowserGame:
    async with db.begin():
        game = await get_game(db, game_id, lock=True)
        if game.status == "closed":
            raise SessionClosed("Game is finished")
        state = HumanGame(
            tuple(tuple(ship) for ship in game.player_fleet),
            tuple(tuple(ship) for ship in game.bot_fleet),
            dict(game.player_shots),
            dict(game.bot_shots),
        )
        state.fire(coordinate, rng)
        game.player_shots, game.bot_shots = state.player_shots, state.bot_shots
        game.winner = state.winner
        if state.winner is not None:
            game.status = "closed"
    return game


async def close(db: AsyncSession, game_id: UUID) -> BrowserGame:
    async with db.begin():
        game = await get_game(db, game_id, lock=True)
        game.status = "closed"
    return game
