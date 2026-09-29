import json
from unittest.mock import AsyncMock

import pytest

from battleship.arena.cli import main, single_match
from battleship.arena.models import MatchResult, Player


def test_match_command(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(
        "sys.argv", ["arena", "--output", str(tmp_path), "match", "http://first", "http://second"]
    )
    result = MatchResult(("first", "second"), "first", winner="first")
    monkeypatch.setattr("battleship.arena.cli.single_match", AsyncMock(return_value=[result]))
    main()
    assert (tmp_path / "results.json").exists()
    assert "first" in capsys.readouterr().out


def test_tournament_command(monkeypatch, tmp_path):
    players = tmp_path / "players.json"
    players.write_text(
        json.dumps([{"name": "a", "url": "http://a"}, {"name": "b", "url": "http://b"}])
    )
    monkeypatch.setattr(
        "sys.argv", ["arena", "--output", str(tmp_path), "tournament", str(players)]
    )
    monkeypatch.setattr("battleship.arena.cli.run_tournament", AsyncMock(return_value=[]))
    main()
    assert (tmp_path / "standings.csv").exists()


def test_invalid_command_arguments(monkeypatch):
    monkeypatch.setattr("sys.argv", ["arena", "match", "not-a-url", "http://second"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2


async def test_single_match_helper(monkeypatch):
    expected = MatchResult(("a", "b"), "a", winner="a")
    monkeypatch.setattr("battleship.arena.cli.play_match", AsyncMock(return_value=expected))
    assert await single_match(
        [Player(name="a", url="http://a"), Player(name="b", url="http://b")]
    ) == [expected]
