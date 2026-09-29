from dataclasses import dataclass
from typing import Literal

from battleship.domain.board import ShotResult
from battleship.domain.errors import AlreadyClosed, Conflict, SessionClosed

Turn = Literal["unknown", "self", "opponent"]
Status = Literal["active", "closed"]


@dataclass
class GameState:
    status: Status = "active"
    turn: Turn = "unknown"
    pending_shot: str | None = None

    def require_active(self) -> None:
        if self.status == "closed":
            raise SessionClosed("Session is closed")

    def require_shot(self) -> None:
        self.require_active()
        if self.turn == "opponent" or self.pending_shot is not None:
            raise Conflict("Not awaiting our next shot")

    def request_shot(self, coordinate: str) -> None:
        self.require_shot()
        self.turn = "self"
        self.pending_shot = coordinate

    def accept_result(self, result: ShotResult) -> str:
        self.require_active()
        if self.pending_shot is None or self.turn != "self":
            raise Conflict("No shot is awaiting a result")
        coordinate = self.pending_shot
        self.pending_shot = None
        self.turn = "opponent" if result == "miss" else "self"
        return coordinate

    def require_opponent_shot(self) -> None:
        self.require_active()
        if self.turn == "self" or self.pending_shot is not None:
            raise Conflict("Not the opponent's turn")

    def receive_shot(self, result: ShotResult) -> None:
        self.require_opponent_shot()
        self.turn = "self" if result == "miss" else "opponent"

    def close(self) -> None:
        if self.status == "closed":
            raise AlreadyClosed("Session is already closed")
        self.status = "closed"
