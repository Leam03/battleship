import os

from battleship.arena.models import Player
from battleship.arena.tournament import build_standings, run_tournament


async def test_tournament_balances_first_move():
    players = [
        Player(name="a", url=os.environ["BATTLESHIP_FIRST_URL"]),
        Player(name="b", url=os.environ["BATTLESHIP_SECOND_URL"]),
    ]
    matches = await run_tournament(players, games_per_pair=2, concurrency=2)
    assert len(matches) == 2
    assert [m.first for m in matches] == ["a", "b"]
    assert all(not m.failures for m in matches)
    assert sum(row.wins for row in build_standings(players, matches)) == 2
