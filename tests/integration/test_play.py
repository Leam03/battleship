import asyncio
from uuid import UUID, uuid4

import pytest

from battleship.db.models import BrowserGame
from battleship.domain.fleet import FALLBACK

PLACEMENT = {"ships": [{"coordinates": list(ship)} for ship in FALLBACK]}


async def start(client):
    response = await client.post("/play/games", json=PLACEMENT)
    assert response.status_code == 201
    return response.json()


async def test_browser_game_keeps_custom_fleet_and_hides_enemy(client, sessions):
    data = await start(client)
    assert data["ships"] == PLACEMENT["ships"]
    assert "enemy_ships" not in data
    assert data["shots"] == data["enemy_shots"] == {}
    assert (await client.get(f"/play/games/{data['id']}")).json() == data
    async with sessions() as db:
        stored = await db.get(BrowserGame, UUID(data["id"]))
        assert stored.player_fleet == [list(ship) for ship in FALLBACK]
        assert len(stored.bot_fleet) == 10


async def test_player_can_finish_a_game_and_reveal_enemy(client, sessions):
    data = await start(client)
    path = f"/play/games/{data['id']}"
    async with sessions() as db:
        enemy = (await db.get(BrowserGame, UUID(data["id"]))).bot_fleet
    for ship in enemy:
        for coordinate in ship:
            response = await client.post(path + "/shot", json={"coordinate": coordinate})
            assert response.status_code == 200
    final = response.json()
    assert final["winner"] == "player" and final["status"] == "closed"
    assert final["enemy_shots"] == {}
    assert final["enemy_ships"] == [{"coordinates": ship} for ship in enemy]
    assert (await client.post(path + "/shot", json={"coordinate": "A1"})).status_code == 410


async def test_miss_triggers_bot_and_duplicate_is_atomic(client, sessions):
    data = await start(client)
    path = f"/play/games/{data['id']}"
    async with sessions() as db:
        enemy = (await db.get(BrowserGame, UUID(data["id"]))).bot_fleet
    occupied = {cell for ship in enemy for cell in ship}
    water = next(f"{x}{y}" for x in "ABCDEFGHIJ" for y in range(1, 11) if f"{x}{y}" not in occupied)
    responses = await asyncio.gather(
        *(client.post(path + "/shot", json={"coordinate": water}) for _ in range(2))
    )
    assert sorted(response.status_code for response in responses) == [200, 400]
    saved = (await client.get(path)).json()
    assert saved["shots"] == {water: "miss"}
    assert saved["enemy_shots"]
    assert "enemy_ships" not in saved


async def test_close_preserves_history_and_is_idempotent(client):
    data = await start(client)
    path = f"/play/games/{data['id']}"
    assert (await client.post(path + "/close")).json()["status"] == "closed"
    assert (await client.post(path + "/close")).status_code == 200
    assert (await client.post(path + "/shot", json={"coordinate": "A1"})).status_code == 410


@pytest.mark.parametrize("ships", [[], PLACEMENT["ships"][:-1], [PLACEMENT["ships"][0]] * 10])
async def test_reject_invalid_fleet(client, ships):
    assert (await client.post("/play/games", json={"ships": ships})).status_code == 400


@pytest.mark.parametrize("game_id", [str(uuid4()), "broken"])
async def test_missing_game(client, game_id):
    path = f"/play/games/{game_id}"
    assert (await client.get(path)).status_code == 404
    assert (await client.post(path + "/shot", json={"coordinate": "A1"})).status_code == 404
    assert (await client.post(path + "/close")).status_code == 404
