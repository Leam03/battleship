from random import Random

import pytest

from battleship.domain.board import resolve_shot
from battleship.domain.errors import InvalidInput, SessionClosed
from battleship.domain.fleet import FALLBACK, generate_fleet
from battleship.domain.play import HumanGame
from battleship.domain.targeting import choose_shot


def test_hit_preserves_player_turn_and_last_hit_wins():
    game = HumanGame(FALLBACK, FALLBACK)
    for ship in FALLBACK:
        for cell in ship:
            game.fire(cell, Random(0))
    assert game.winner == "player"
    assert len(game.player_shots) == 20
    assert game.bot_shots == {}
    with pytest.raises(SessionClosed):
        game.fire("J10", Random(0))


def test_bot_continues_after_hits_and_stops_after_miss(monkeypatch):
    targets = iter(["A1", "B1", "C1", "D1", "J10"])
    monkeypatch.setattr("battleship.domain.play.choose_shot", lambda *args: next(targets))
    game = HumanGame(FALLBACK, FALLBACK)
    game.fire("J10", Random(0))
    assert game.player_shots == {"J10": "miss"}
    assert list(game.bot_shots.values()) == ["hit", "hit", "hit", "killed", "miss"]
    assert game.winner is None


def test_bot_wins_on_last_ship(monkeypatch):
    game = HumanGame(FALLBACK, FALLBACK)
    for ship in FALLBACK[:-1]:
        for cell in ship:
            game.bot_shots[cell] = resolve_shot(FALLBACK, game.bot_shots, cell)
    monkeypatch.setattr("battleship.domain.play.choose_shot", lambda *args: "F9")
    game.fire("J10", Random(0))
    assert game.winner == "bot"
    assert game.bot_shots["F9"] == "killed"


@pytest.mark.parametrize("cell", ["A1", "Z1", "A01"])
def test_invalid_or_repeated_shot_does_not_change_state(cell):
    game = HumanGame(FALLBACK, FALLBACK, player_shots={"A1": "hit"})
    with pytest.raises(InvalidInput):
        game.fire(cell, Random(0))
    assert game.player_shots == {"A1": "hit"}
    assert game.bot_shots == {}


@pytest.mark.parametrize("seed", range(10))
def test_complete_games_have_a_winner_and_no_repeated_shots(seed):
    rng = Random(seed)
    game = HumanGame(generate_fleet(rng), generate_fleet(rng))
    for _ in range(100):
        if game.winner:
            break
        game.fire(choose_shot(game.player_shots, rng), rng)
    assert game.winner in {"player", "bot"}
    winner_shots = game.player_shots if game.winner == "player" else game.bot_shots
    assert sum(result != "miss" for result in winner_shots.values()) == 20
