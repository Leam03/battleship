from collections import Counter
from collections.abc import Sequence
from functools import cache
from random import Random

from battleship.domain.coordinates import (
    BOARD_SIZE,
    Cell,
    format_coordinate,
    parse_coordinate,
    surrounding_cells,
)
from battleship.domain.errors import InvalidInput

FLEET_SIZES = (4, 3, 3, 2, 2, 2, 1, 1, 1, 1)
Fleet = tuple[tuple[str, ...], ...]
FALLBACK: Fleet = (
    ("A1", "B1", "C1", "D1"),
    ("F1", "F2", "F3"),
    ("H1", "H2", "H3"),
    ("A4", "B4"),
    ("D5", "D6"),
    ("G5", "H5"),
    ("J1",),
    ("J4",),
    ("B8",),
    ("F9",),
)


def validate_ship(ship: Sequence[str]) -> frozenset[Cell]:
    cells = frozenset(parse_coordinate(value) for value in ship)
    if not cells or len(cells) != len(ship):
        raise InvalidInput("Ship must contain distinct cells")
    xs, ys = {x for x, _ in cells}, {y for _, y in cells}
    if len(xs) != 1 and len(ys) != 1:
        raise InvalidInput("Ship must be straight")
    axis = sorted(ys if len(xs) == 1 else xs)
    if axis[-1] - axis[0] + 1 != len(cells):
        raise InvalidInput("Ship must not have gaps")
    return cells


def validate_fleet(fleet: Sequence[Sequence[str]]) -> None:
    if Counter(map(len, fleet)) != Counter(FLEET_SIZES):
        raise InvalidInput("Fleet must contain ships of lengths 4,3,3,2,2,2,1,1,1,1")
    blocked: frozenset[Cell] = frozenset()
    for ship in fleet:
        cells = validate_ship(ship)
        if cells & blocked:
            raise InvalidInput("Ships must not overlap or touch")
        blocked |= surrounding_cells(cells)


@cache
def ship_placements(length: int) -> tuple[frozenset[Cell], ...]:
    return tuple(
        frozenset((x + dx * step, y + dy * step) for step in range(length))
        for dx, dy in (((1, 0),) if length == 1 else ((1, 0), (0, 1)))
        for y in range(BOARD_SIZE - dy * (length - 1))
        for x in range(BOARD_SIZE - dx * (length - 1))
    )


def generate_fleet(rng: Random, max_steps: int = 10_000) -> Fleet:
    steps = 0

    def place(index: int, blocked: frozenset[Cell]) -> list[frozenset[Cell]] | None:
        nonlocal steps
        if index == len(FLEET_SIZES):
            return []
        candidates = list(ship_placements(FLEET_SIZES[index]))
        rng.shuffle(candidates)
        for cells in candidates:
            steps += 1
            if steps > max_steps:
                return None
            if cells & blocked:
                continue
            tail = place(index + 1, blocked | surrounding_cells(cells))
            if tail is not None:
                return [cells, *tail]
        return None

    placed = place(0, frozenset())
    if placed is not None:
        return tuple(tuple(format_coordinate(cell) for cell in sorted(ship)) for ship in placed)

    turns, reflect = rng.randrange(4), rng.choice((True, False))

    def transform(coordinate: str) -> str:
        x, y = parse_coordinate(coordinate)
        if reflect:
            x = 9 - x
        for _ in range(turns):
            x, y = 9 - y, x
        return format_coordinate((x, y))

    fleet = tuple(tuple(transform(cell) for cell in ship) for ship in FALLBACK)
    validate_fleet(fleet)
    return fleet
