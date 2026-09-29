import re

from battleship.domain.errors import InvalidInput

BOARD_SIZE = 10
Cell = tuple[int, int]
ALL_CELLS = tuple((x, y) for y in range(BOARD_SIZE) for x in range(BOARD_SIZE))
COORDINATE = re.compile(r"[A-J](?:10|[1-9])", flags=re.ASCII)


def parse_coordinate(value: str) -> Cell:
    if not isinstance(value, str) or COORDINATE.fullmatch(value) is None:
        raise InvalidInput("Coordinate must be in A1–J10 format")
    return ord(value[0]) - ord("A"), int(value[1:]) - 1


def format_coordinate(cell: Cell) -> str:
    x, y = cell
    if not (0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE):
        raise InvalidInput("Cell is outside the board")
    return f"{chr(ord('A') + x)}{y + 1}"


def neighbors(cell: Cell) -> frozenset[Cell]:
    x, y = cell
    return frozenset(
        (a, b)
        for a, b in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))
        if 0 <= a < BOARD_SIZE and 0 <= b < BOARD_SIZE
    )


def surrounding_cells(cells: frozenset[Cell]) -> frozenset[Cell]:
    return frozenset(
        (x + dx, y + dy)
        for x, y in cells
        for dx in (-1, 0, 1)
        for dy in (-1, 0, 1)
        if 0 <= x + dx < BOARD_SIZE and 0 <= y + dy < BOARD_SIZE
    )
