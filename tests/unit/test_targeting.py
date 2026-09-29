from random import Random

import pytest

from battleship.domain.board import resolve_shot
from battleship.domain.coordinates import neighbors, parse_coordinate
from battleship.domain.errors import Conflict
from battleship.domain.fleet import generate_fleet
from battleship.domain.targeting import analyze_history, choose_shot


@pytest.mark.parametrize("seed", range(30))
def test_complete_fleet_without_repeats(seed):
    fleet = generate_fleet(Random(seed))
    history = {}
    hits = 0
    for _ in range(100):
        target = choose_shot(history, Random(seed + len(history)))
        assert target not in history
        result = resolve_shot(fleet, history, target)
        history[target] = result
        hits += result != "miss"
        if hits == 20:
            break
    assert hits == 20
    with pytest.raises(Conflict):
        choose_shot(history, Random(seed))


@pytest.mark.parametrize("seed", range(10))
def test_finishes_wounded_ship(seed):
    assert parse_coordinate(choose_shot({"E5": "hit"}, Random(seed))) in neighbors((4, 4))
    assert choose_shot({"E5": "hit", "E6": "hit"}, Random(seed)) in {"E4", "E7"}
    assert choose_shot({"A1": "hit", "A3": "hit"}, Random(seed)) in {"A2", "A4"}


def test_history_tracks_sunk_ships_and_blocks_halo():
    state = analyze_history({"A1": "hit", "A2": "killed", "E5": "hit", "J10": "miss"})
    assert state.remaining.count(2) == 2
    assert state.wounded == {(4, 4)}
    assert {(0, 0), (0, 1), (1, 2), (9, 9)} <= state.blocked


def test_impossible_history_is_rejected():
    with pytest.raises(Conflict):
        analyze_history({f"A{i}": "hit" if i < 5 else "killed" for i in range(1, 6)})
    with pytest.raises(Conflict):
        choose_shot({f"{x}{y}": "miss" for x in "ABCDEFGHIJ" for y in range(1, 11)}, Random(1))
