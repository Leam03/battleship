from pathlib import Path
from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import Field

from battleship.api.dependencies import Database, RandomSource
from battleship.api.schemas import Message, Ship, ShotCoordinate
from battleship.db.models import BrowserGame
from battleship.domain.board import ShotResult
from battleship.domain.fleet import generate_fleet
from battleship.domain.play import Winner
from battleship.domain.state import Status
from battleship.services import play

STATIC_DIRECTORY = Path(__file__).resolve().parents[1] / "static"
router = APIRouter(tags=["browser"])


class Placement(Message):
    ships: list[Ship] = Field(min_length=10, max_length=10)


class BrowserState(Message):
    id: UUID
    status: Status
    winner: Winner | None
    ships: list[Ship]
    shots: dict[str, ShotResult]
    enemy_shots: dict[str, ShotResult]
    enemy_ships: list[Ship] | None = None


def view(game: BrowserGame) -> BrowserState:
    return BrowserState(
        id=game.id,
        status=game.status,
        winner=game.winner,
        ships=[Ship(coordinates=ship) for ship in game.player_fleet],
        shots=game.player_shots,
        enemy_shots=game.bot_shots,
        enemy_ships=(
            [Ship(coordinates=ship) for ship in game.bot_fleet] if game.status == "closed" else None
        ),
    )


@router.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC_DIRECTORY / "index.html", headers={"Cache-Control": "no-cache"})


@router.get("/play/fleet", response_model=Placement)
async def random_fleet(rng: RandomSource) -> Placement:
    return Placement(ships=[Ship(coordinates=list(ship)) for ship in generate_fleet(rng)])


@router.post("/play/games", status_code=201, response_model_exclude_none=True)
async def create_game(body: Placement, db: Database, rng: RandomSource) -> BrowserState:
    fleet = tuple(tuple(ship.coordinates) for ship in body.ships)
    return view(await play.create_game(db, fleet, rng))


@router.get("/play/games/{game_id}", response_model_exclude_none=True)
async def get_game(game_id: UUID, db: Database) -> BrowserState:
    return view(await play.get_game(db, game_id))


@router.post("/play/games/{game_id}/shot", response_model_exclude_none=True)
async def fire(
    game_id: UUID, body: ShotCoordinate, db: Database, rng: RandomSource
) -> BrowserState:
    return view(await play.fire(db, game_id, body.coordinate, rng))


@router.post("/play/games/{game_id}/close", response_model_exclude_none=True)
async def close(game_id: UUID, db: Database) -> BrowserState:
    return view(await play.close(db, game_id))
