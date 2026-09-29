from uuid import uuid4

import pytest
from sqlalchemy import select

from battleship.db.models import GameSession, Shot
from battleship.domain.fleet import validate_fleet


async def new_game(client):
    response = await client.post("/game")
    assert response.status_code == 201
    data = response.json()
    validate_fleet([ship["coordinates"] for ship in data["ships"]])
    return data


async def test_full_api_cycle(client, sessions):
    data = await new_game(client)
    session_id = data["session_id"]
    path = f"/game/{session_id}"
    assert (await client.post(f"{path}/shot/result", json={"result": "hit"})).status_code == 409
    target = await client.post(f"{path}/shot")
    assert target.status_code == 200
    assert (await client.post(f"{path}/shot")).status_code == 409
    assert (
        await client.post(f"{path}/opponent-shot", json={"coordinate": "A1"})
    ).status_code == 409
    for outcome in ("hit", "killed", "miss"):
        response = await client.post(f"{path}/shot/result", json={"result": outcome})
        assert response.json() == {"status": "accepted"}
        if outcome != "miss":
            assert (await client.post(f"{path}/shot")).status_code == 200
    assert (await client.post(f"{path}/shot")).status_code == 409
    occupied = {c for s in data["ships"] for c in s["coordinates"]}
    water = next(f"{x}{y}" for x in "ABCDEFGHIJ" for y in range(1, 11) if f"{x}{y}" not in occupied)
    assert (await client.post(f"{path}/opponent-shot", json={"coordinate": water})).json() == {
        "result": "miss"
    }
    assert (
        await client.post(f"{path}/opponent-shot", json={"coordinate": water})
    ).status_code == 400
    async with sessions() as db:
        shots = list(await db.scalars(select(Shot)))
        assert len(shots) == 4
        assert any(shot.direction == "incoming" and shot.result == "miss" for shot in shots)
    assert (await client.post(f"{path}/close")).json() == {"status": "closed"}
    assert (await client.post(f"{path}/close")).status_code == 400
    for suffix, body in [
        ("shot", None),
        ("shot/result", {"result": "hit"}),
        ("opponent-shot", {"coordinate": "A1"}),
    ]:
        assert (await client.post(f"{path}/{suffix}", json=body)).status_code == 410
    async with sessions() as db:
        game = await db.scalar(select(GameSession))
        assert game.closed_at is not None


async def test_all_twenty_hits_match_initial_fleet(client):
    data = await new_game(client)
    path = f"/game/{data['session_id']}"
    for ship in data["ships"]:
        for index, coordinate in enumerate(ship["coordinates"]):
            response = await client.post(f"{path}/opponent-shot", json={"coordinate": coordinate})
            expected = "killed" if index == len(ship["coordinates"]) - 1 else "hit"
            assert response.status_code == 200
            assert response.json() == {"result": expected}
    assert (await client.post(f"{path}/close")).status_code == 200


@pytest.mark.parametrize("session_id", [str(uuid4()), "invalid"])
@pytest.mark.parametrize(
    "suffix, body",
    [
        ("shot", None),
        ("shot/result", {"result": "hit"}),
        ("opponent-shot", {"coordinate": "A1"}),
        ("close", None),
    ],
)
async def test_missing_sessions(client, session_id, suffix, body):
    response = await client.post(f"/game/{session_id}/{suffix}", json=body)
    assert response.status_code == 404
    assert isinstance(response.json()["detail"], str)


async def test_health_and_ready(client):
    assert (await client.get("/health")).json() == {"status": "ok"}
    assert (await client.get("/ready")).json() == {"status": "ready"}
