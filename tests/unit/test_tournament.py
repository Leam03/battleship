import csv
import json
from collections import Counter

import pytest

from battleship.arena.models import MatchResult, Player
from battleship.arena.tournament import (
    build_schedule,
    build_standings,
    run_tournament,
    write_results,
)

PLAYERS = [Player(name=n, url=f"http://{n}") for n in ("a", "b", "c")]


def test_balanced_schedule():
    schedule = build_schedule(PLAYERS, 4)
    assert len(schedule) == 12
    assert Counter(p.name for p, _ in schedule) == {"a": 4, "b": 4, "c": 4}
    assert all(a.name != b.name for a, b in schedule)


@pytest.mark.parametrize(
    "players, games", [(PLAYERS[:1], 2), ([PLAYERS[0]] * 2, 2), (PLAYERS, 1), (PLAYERS, 0)]
)
def test_invalid_schedule(players, games):
    with pytest.raises(ValueError):
        build_schedule(players, games)


def test_standings_and_export(tmp_path):
    matches = [
        MatchResult(("a", "b"), "a", winner="a", failures={"b": ["timeout"]}),
        MatchResult(("b", "c"), "b", winner="c"),
        MatchResult(("a", "c"), "a", failures={"a": ["offline"], "c": ["offline"]}),
    ]
    table = build_standings(PLAYERS, matches)
    assert [r.rank for r in table] == [1, 1, 3]
    assert [r.name for r in table] == ["a", "c", "b"]
    assert table[0].unscored == 1
    assert table[2].technical_failures == 1
    write_results(tmp_path, PLAYERS, matches)
    assert len(json.loads((tmp_path / "results.json").read_text())["matches"]) == 3
    assert "technical_failures" in (tmp_path / "standings.csv").read_text()


async def test_tournament_runs_all_matches(monkeypatch):
    async def play(first, second, http):
        return MatchResult((first.name, second.name), first.name, winner=first.name)

    monkeypatch.setattr("battleship.arena.tournament.play_match", play)
    assert len(await run_tournament(PLAYERS, 2, 2)) == 6
    with pytest.raises(ValueError):
        await run_tournament(PLAYERS, 2, 0)


@pytest.mark.parametrize("name", ["=1+1", "+1+1", "-1+1", "@SUM(1)", "\t=1+1", " \r=1+1"])
def test_csv_names_are_text_and_json_keeps_original_names(tmp_path, name):
    players = [Player(name=name, url="http://first"), Player(name="second", url="http://second")]
    write_results(tmp_path, players, [])
    data = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    assert name in {row["name"] for row in data["standings"]}
    with (tmp_path / "standings.csv").open(newline="", encoding="utf-8") as stream:
        names = {row["name"] for row in csv.DictReader(stream)}
    assert "'" + name in names
