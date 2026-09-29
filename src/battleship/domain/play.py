from dataclasses import dataclass, field
from random import Random
from typing import Literal

from battleship.domain.board import ShotResult, is_defeated, resolve_shot
from battleship.domain.errors import SessionClosed
from battleship.domain.fleet import Fleet
from battleship.domain.targeting import choose_shot

Winner = Literal["player", "bot"]


@dataclass
class HumanGame:
    player_fleet: Fleet
    bot_fleet: Fleet
    player_shots: dict[str, ShotResult] = field(default_factory=dict)
    bot_shots: dict[str, ShotResult] = field(default_factory=dict)
    winner: Winner | None = None

    def fire(self, coordinate: str, rng: Random) -> None:
        if self.winner is not None:
            raise SessionClosed("Game is finished")
        result = resolve_shot(self.bot_fleet, self.player_shots, coordinate)
        self.player_shots[coordinate] = result
        if is_defeated(self.bot_fleet, self.player_shots):
            self.winner = "player"
        if result != "miss":
            return
        while True:
            target = choose_shot(self.bot_shots, rng)
            outcome = resolve_shot(self.player_fleet, self.bot_shots, target)
            self.bot_shots[target] = outcome
            if is_defeated(self.player_fleet, self.bot_shots):
                self.winner = "bot"
                return
            if outcome == "miss":
                return
