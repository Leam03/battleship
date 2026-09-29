import pytest
from pydantic import ValidationError

from battleship.api.schemas import GameCreated, Ship
from battleship.arena.models import Player, TechnicalDefeat
from battleship.arena.referee import RefereeBoard


def test_twenty_misses_do_not_win():
    board = RefereeBoard("test", (frozenset({"A1", "A2"}),))
    for x in "BC":
        for y in range(1, 11):
            board.check_result(f"{x}{y}", "miss")
    assert not board.has_won()
    board.check_result("A1", "hit")
    assert not board.has_won()
    board.check_result("A2", "killed")
    assert board.has_won()


@pytest.mark.parametrize("coordinate, result", [("A1", "miss"), ("A1", "killed"), ("J10", "hit")])
def test_rejects_lies(coordinate, result):
    board = RefereeBoard("test", (frozenset({"A1", "A2"}),))
    with pytest.raises(TechnicalDefeat):
        board.check_result(coordinate, result)
    assert board.received == set()


def test_rejects_invalid_fleet():
    from uuid import uuid4

    response = GameCreated(session_id=uuid4(), ships=[Ship(coordinates=["A1"])])
    with pytest.raises(TechnicalDefeat):
        RefereeBoard.from_start("test", response)


@pytest.mark.parametrize(
    "url", ["ftp://host", "http://", "http://u:p@host", "http://host?q=1", "http://host#part"]
)
def test_invalid_player_urls(url):
    with pytest.raises(ValidationError):
        Player(name="one", url=url)


def test_empty_player_name():
    with pytest.raises(ValidationError):
        Player(name=" ", url="http://host")
