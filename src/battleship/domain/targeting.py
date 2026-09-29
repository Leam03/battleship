from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from random import Random

from battleship.domain.board import ShotResult
from battleship.domain.coordinates import (
    ALL_CELLS,
    Cell,
    format_coordinate,
    neighbors,
    parse_coordinate,
    surrounding_cells,
)
from battleship.domain.errors import Conflict
from battleship.domain.fleet import FLEET_SIZES, ship_placements


@dataclass(frozen=True)
class TargetMap:
    fired: frozenset[Cell]
    blocked: frozenset[Cell]
    wounded: frozenset[Cell]
    remaining: tuple[int, ...]


def analyze_history(history: Mapping[str, ShotResult]) -> TargetMap:
    fired = frozenset(parse_coordinate(c) for c in history)
    misses = frozenset(parse_coordinate(c) for c, r in history.items() if r == "miss")
    hits = set(fired - misses)
    kills = {parse_coordinate(c) for c, r in history.items() if r == "killed"}
    remaining = list(FLEET_SIZES)
    sunk: frozenset[Cell] = frozenset()
    wounded: frozenset[Cell] = frozenset()
    while hits:
        component = {hits.pop()}
        frontier = list(component)
        while frontier:
            adjacent = neighbors(frontier.pop()) & hits
            hits.difference_update(adjacent)
            component.update(adjacent)
            frontier.extend(adjacent)
        if component & kills:
            if len(component) not in remaining:
                raise Conflict("Shot history contradicts fleet composition")
            remaining.remove(len(component))
            sunk |= frozenset(component)
        else:
            wounded |= frozenset(component)
    return TargetMap(fired, misses | surrounding_cells(sunk), wounded, tuple(remaining))


def target_candidates(length: int, state: TargetMap) -> tuple[frozenset[Cell], ...]:
    return tuple(
        cells
        for cells in ship_placements(length)
        if not cells & state.blocked
        and (not state.wounded or cells & state.wounded)
        and not ((surrounding_cells(cells) - cells) & state.wounded)
        and bool(cells - state.fired)
    )


def score_cells(state: TargetMap) -> Counter[Cell]:
    scores: Counter[Cell] = Counter()
    for length, count in Counter(state.remaining).items():
        for cells in target_candidates(length, state):
            weight = count * (1 + len(cells & state.wounded))
            for cell in cells - state.fired:
                scores[cell] += weight
    return scores


def choose_shot(history: Mapping[str, ShotResult], rng: Random) -> str:
    state = analyze_history(history)
    available = set(ALL_CELLS) - state.fired - state.blocked
    if not available or not state.remaining:
        raise Conflict("No valid targets remain")
    scores = score_cells(state)
    if state.wounded:
        adjacent = set().union(*(neighbors(cell) for cell in state.wounded)) & available
        if adjacent:
            available = adjacent
    best = max((scores[cell] for cell in available), default=0)
    candidates = sorted(cell for cell in available if scores[cell] == best)
    return format_coordinate(rng.choice(candidates))
