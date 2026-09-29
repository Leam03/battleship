import asyncio
from random import Random
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError

from battleship.db.models import GameSession, Shot
from battleship.services.game import make_shot


async def test_two_requests_produce_one_pending_shot(client, sessions):
    session_id = (await client.post("/game")).json()["session_id"]
    responses = await asyncio.gather(*(client.post(f"/game/{session_id}/shot") for _ in range(2)))
    assert sorted(r.status_code for r in responses) == [200, 409]
    async with sessions() as db:
        shots = list(await db.scalars(select(Shot)))
        assert len(shots) == 1
        assert shots[0].result is None
    results = await asyncio.gather(
        *(client.post(f"/game/{session_id}/shot/result", json={"result": "hit"}) for _ in range(2))
    )
    assert sorted(r.status_code for r in results) == [200, 409]


async def test_parallel_incoming_hits_are_not_lost(client, sessions):
    data = (await client.post("/game")).json()
    cells = next(s["coordinates"] for s in data["ships"] if len(s["coordinates"]) == 2)
    responses = await asyncio.gather(
        *(
            client.post(f"/game/{data['session_id']}/opponent-shot", json={"coordinate": c})
            for c in cells
        )
    )
    assert all(r.status_code == 200 for r in responses)
    assert sorted(r.json()["result"] for r in responses) == ["hit", "killed"]
    async with sessions() as db:
        assert len(list(await db.scalars(select(Shot)))) == 2


async def test_close_is_atomic(client):
    session_id = (await client.post("/game")).json()["session_id"]
    responses = await asyncio.gather(*(client.post(f"/game/{session_id}/close") for _ in range(2)))
    assert sorted(r.status_code for r in responses) == [200, 400]


async def test_distinct_games_are_isolated(client, sessions):
    games = await asyncio.gather(*(client.post("/game") for _ in range(10)))
    ids = [r.json()["session_id"] for r in games]
    assert len(set(ids)) == 10
    shots = await asyncio.gather(*(client.post(f"/game/{sid}/shot") for sid in ids))
    assert all(r.status_code == 200 for r in shots)
    await client.post(f"/game/{ids[0]}/shot/result", json={"result": "miss"})
    async with sessions() as db:
        games = list(await db.scalars(select(GameSession)))
        assert sum(g.pending_shot is not None for g in games) == 9
        assert sum(g.turn == "opponent" for g in games) == 1


async def test_close_racing_with_shot_keeps_history_consistent(client, sessions):
    session_id = (await client.post("/game")).json()["session_id"]
    shot, close = await asyncio.gather(
        client.post(f"/game/{session_id}/shot"),
        client.post(f"/game/{session_id}/close"),
    )
    assert close.status_code == 200
    assert shot.status_code in {200, 410}
    async with sessions() as db:
        game = await db.get(GameSession, UUID(session_id))
        shots = list(await db.scalars(select(Shot)))
        assert game.status == "closed"
        assert len(shots) == int(shot.status_code == 200)
        assert game.pending_shot == (shots[0].coordinate if shots else None)


async def test_lock_timeout_does_not_change_game_or_block_other_sessions(client, sessions):
    first = (await client.post("/game")).json()["session_id"]
    second = (await client.post("/game")).json()["session_id"]
    async with sessions() as blocker, blocker.begin():
        await blocker.scalar(
            select(GameSession).where(GameSession.id == UUID(first)).with_for_update()
        )
        async with sessions() as contender:
            with pytest.raises(DBAPIError):
                await make_shot(contender, UUID(first), Random(0))
            assert not contender.in_transaction()
        assert (await client.post(f"/game/{second}/shot")).status_code == 200
    async with sessions() as db:
        game = await db.get(GameSession, UUID(first))
        assert game.pending_shot is None
        assert game.sequence == 0
    assert (await client.post(f"/game/{first}/shot")).status_code == 200
