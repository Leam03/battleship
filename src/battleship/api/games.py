from typing import Any
from uuid import UUID

from fastapi import APIRouter

from battleship.api.dependencies import Database, RandomSource
from battleship.api.schemas import (
    Accepted,
    Closed,
    ErrorResponse,
    GameCreated,
    Ship,
    ShotCoordinate,
    ShotOutcome,
)
from battleship.services import game

router = APIRouter(tags=["game"], responses={500: {"model": ErrorResponse}})
ERRORS: dict[int | str, dict[str, Any]] = {
    code: {"model": ErrorResponse} for code in (400, 404, 409, 410)
}
SHOT_ERRORS: dict[int | str, dict[str, Any]] = {
    code: {"model": ErrorResponse} for code in (404, 409, 410)
}
CLOSE_ERRORS: dict[int | str, dict[str, Any]] = {
    code: {"model": ErrorResponse} for code in (400, 404)
}


@router.post("/game", response_model=GameCreated, status_code=201)
async def create_game(db: Database, rng: RandomSource) -> GameCreated:
    created = await game.create_game(db, rng)
    return GameCreated(session_id=created.id, ships=[Ship(coordinates=s) for s in created.fleet])


@router.post("/game/{session_id}/shot", response_model=ShotCoordinate, responses=SHOT_ERRORS)
async def make_shot(session_id: UUID, db: Database, rng: RandomSource) -> ShotCoordinate:
    return ShotCoordinate(coordinate=await game.make_shot(db, session_id, rng))


@router.post("/game/{session_id}/shot/result", response_model=Accepted, responses=ERRORS)
async def accept_result(session_id: UUID, body: ShotOutcome, db: Database) -> Accepted:
    await game.accept_shot_result(db, session_id, body.result)
    return Accepted(status="accepted")


@router.post("/game/{session_id}/opponent-shot", response_model=ShotOutcome, responses=ERRORS)
async def receive_shot(session_id: UUID, body: ShotCoordinate, db: Database) -> ShotOutcome:
    result = await game.receive_opponent_shot(db, session_id, body.coordinate)
    return ShotOutcome(result=result)


@router.post("/game/{session_id}/close", response_model=Closed, responses=CLOSE_ERRORS)
async def close_game(session_id: UUID, db: Database) -> Closed:
    await game.close_game(db, session_id)
    return Closed(status="closed")
