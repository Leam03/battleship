from dataclasses import dataclass, field

from battleship.api.schemas import GameCreated
from battleship.arena.models import TechnicalDefeat
from battleship.domain.board import ShotResult
from battleship.domain.errors import InvalidInput
from battleship.domain.fleet import validate_fleet


@dataclass
class RefereeBoard:
    player: str
    ships: tuple[frozenset[str], ...]
    received: set[str] = field(default_factory=set)

    @classmethod
    def from_start(cls, player: str, response: GameCreated) -> "RefereeBoard":
        fleet = tuple(tuple(ship.coordinates) for ship in response.ships)
        try:
            validate_fleet(fleet)
        except InvalidInput as exc:
            raise TechnicalDefeat(player, f"Invalid fleet: {exc}") from exc
        return cls(player, tuple(frozenset(ship) for ship in fleet))

    def expected_result(self, coordinate: str) -> ShotResult:
        for ship in self.ships:
            if coordinate in ship:
                return "killed" if not ship - self.received - {coordinate} else "hit"
        return "miss"

    def check_result(self, coordinate: str, result: ShotResult) -> None:
        expected = self.expected_result(coordinate)
        if result != expected:
            raise TechnicalDefeat(
                self.player, f"Dishonest result at {coordinate}: expected {expected}, got {result}"
            )
        self.received.add(coordinate)

    def has_won(self) -> bool:
        return all(ship <= self.received for ship in self.ships)
