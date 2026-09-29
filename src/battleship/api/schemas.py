from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints

from battleship.domain.board import ShotResult

Coordinate = Annotated[str, StringConstraints(pattern=r"^[A-J](10|[1-9])$", strict=True)]


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Ship(Message):
    coordinates: list[Coordinate]


class GameCreated(Message):
    session_id: UUID
    ships: list[Ship]


class ShotCoordinate(Message):
    coordinate: Coordinate


class ShotOutcome(Message):
    result: ShotResult


class Accepted(Message):
    status: Literal["accepted"]


class Closed(Message):
    status: Literal["closed"]


class ErrorResponse(Message):
    detail: str
