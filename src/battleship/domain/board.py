from collections.abc import Mapping
from typing import Literal

from battleship.domain.coordinates import parse_coordinate
from battleship.domain.errors import InvalidInput
from battleship.domain.fleet import Fleet

ShotResult = Literal["miss", "hit", "killed"]


def hit_cells(history: Mapping[str, ShotResult]) -> set[str]:
    return {cell for cell, result in history.items() if result != "miss"}


def resolve_shot(fleet: Fleet, history: Mapping[str, ShotResult], coordinate: str) -> ShotResult:
    parse_coordinate(coordinate)
    if coordinate in history:
        raise InvalidInput("Cell has already been shot at")
    hits = hit_cells(history) | {coordinate}
    for ship in fleet:
        if coordinate in ship:
            return "killed" if set(ship) <= hits else "hit"
    return "miss"


def is_defeated(fleet: Fleet, history: Mapping[str, ShotResult]) -> bool:
    return {cell for ship in fleet for cell in ship} <= hit_cells(history)
