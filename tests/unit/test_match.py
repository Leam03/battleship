import httpx
import pytest

from battleship.arena.match import play_match
from battleship.arena.models import Player
from tests.fixtures.fake_services import FakeServices

FIRST = Player(name="first", url="http://first")
SECOND = Player(name="second", url="http://second")


async def test_complete_match_and_cleanup():
    services = FakeServices(water_first=True)
    async with httpx.AsyncClient(transport=httpx.MockTransport(services)) as http:
        result = await play_match(FIRST, SECOND, http)
    assert result.winner in {"first", "second"}
    assert len(result.moves) > 160
    assert not result.failures
    assert len(services.closed) == 2
    assert sum(m.result != "miss" for m in result.moves if m.player == result.winner) == 20
    assert all(t.success for t in result.timings)
    assert result.moves[-1].result == "killed"


@pytest.mark.parametrize("fault", ["fleet", "lie", "repeat", "network", "slow", "close"])
async def test_technical_defeat(fault):
    services = FakeServices({"first": fault})
    async with httpx.AsyncClient(transport=httpx.MockTransport(services)) as http:
        result = await play_match(FIRST, SECOND, http, request_deadline=0.02)
    assert result.winner == "second"
    assert "first" in result.failures
    assert set(services.games) == services.closed


async def test_both_failed():
    services = FakeServices({"first": "fleet", "second": "close"})
    async with httpx.AsyncClient(transport=httpx.MockTransport(services)) as http:
        result = await play_match(FIRST, SECOND, http)
    assert result.winner is None
    assert len(result.failures) == 2


async def test_reject_duplicate_names():
    async with httpx.AsyncClient() as http:
        with pytest.raises(ValueError):
            await play_match(FIRST, FIRST, http)


@pytest.mark.parametrize("operation", ["game", "shot", "close"])
async def test_deep_json_is_a_technical_defeat_and_sessions_are_closed(operation):
    services = FakeServices()
    closed_hosts = set()

    async def respond(request):
        if request.url.path.endswith("/close"):
            closed_hosts.add(request.url.host)
        if request.url.host == "first" and request.url.path.rsplit("/", 1)[-1] == operation:
            return httpx.Response(
                201 if operation == "game" else 200,
                content=b"[" * 30000 + b"0" + b"]" * 30000,
            )
        return await services(request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        result = await play_match(FIRST, SECOND, http)
    assert result.winner == "second"
    assert "first" in result.failures
    assert "second" in closed_hosts
    if operation != "game":
        assert closed_hosts == {"first", "second"}
