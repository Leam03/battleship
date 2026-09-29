import os

import httpx

from battleship.arena.match import play_match
from battleship.arena.models import Player


async def test_two_http_services_finish_a_match():
    first = Player(name="first", url=os.environ["BATTLESHIP_FIRST_URL"])
    second = Player(name="second", url=os.environ["BATTLESHIP_SECOND_URL"])
    async with httpx.AsyncClient(trust_env=False) as client:
        match = await play_match(first, second, client)
        assert match.winner is not None
        assert not match.failures, match.failures
        assert all(t.success and t.elapsed < 1 for t in match.timings)
        hits = sum(move.result != "miss" for move in match.moves if move.player == match.winner)
        assert hits == 20
