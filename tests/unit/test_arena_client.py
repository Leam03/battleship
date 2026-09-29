import asyncio
from uuid import uuid4

import httpx
import pytest

from battleship.api.schemas import Accepted, Closed, GameCreated, ShotCoordinate
from battleship.arena.client import GameClient
from battleship.arena.models import Player, TechnicalDefeat


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(500),
        httpx.Response(302, headers={"location": "http://elsewhere"}),
        httpx.Response(200, content=b"not json"),
        httpx.Response(200, json=[]),
        httpx.Response(200, json={"coordinate": "A01"}),
        httpx.Response(200, json={"coordinate": "A1", "extra": "leak"}),
        httpx.Response(200, content=b"x" * 65_537),
    ],
)
async def test_reject_bad_responses(response):
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: response)) as http:
        client = GameClient(Player(name="test", url="http://test"), http, [])
        with pytest.raises(TechnicalDefeat):
            await client.request("shot", ShotCoordinate)
        assert not client.timings[0].success


async def test_retains_session_id_from_invalid_start_for_cleanup():
    session_id = uuid4()
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(201, json={"session_id": str(session_id), "ships": "invalid"})
        )
    ) as http:
        client = GameClient(Player(name="test", url="http://test"), http, [])
        with pytest.raises(TechnicalDefeat):
            await client.request("start", GameCreated)
        assert client.session_id == session_id


async def test_reject_invalid_session_id():
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(201, json={"session_id": "broken", "ships": []})
        )
    ) as http:
        client = GameClient(Player(name="test", url="http://test"), http, [])
        with pytest.raises(TechnicalDefeat):
            await client.start()
        assert client.session_id is None


class SlowStream(httpx.AsyncByteStream):
    async def __aiter__(self):
        for chunk in [b'{"coordinate":', b'"A1"', b"}"]:
            await asyncio.sleep(0.01)
            yield chunk


async def test_deadline_applies_to_entire_body():
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, stream=SlowStream()))
    ) as http:
        client = GameClient(Player(name="test", url="http://test"), http, [], timeout=0.02)
        with pytest.raises(TechnicalDefeat, match="deadline"):
            await client.shot()


@pytest.mark.parametrize("model", [Accepted, Closed])
async def test_empty_acknowledgment_is_rejected(model):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json={}))
    ) as http:
        client = GameClient(Player(name="test", url="http://test"), http, [])
        with pytest.raises(TechnicalDefeat):
            await client.request("close", model)
