from random import Random
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from battleship.config import Settings
from battleship.db.models import GameSession, Shot
from battleship.db.queries import add_shot
from battleship.domain.errors import Conflict
from battleship.main import create_app
from battleship.services.game import accept_shot_result, make_shot


async def test_pending_shot_survives_new_db_connection(client, sessions):
    session_id = UUID((await client.post("/game")).json()["session_id"])
    coordinate = (await client.post(f"/game/{session_id}/shot")).json()["coordinate"]
    async with sessions() as db:
        await accept_shot_result(db, session_id, "hit")
    async with sessions() as db:
        next_coordinate = await make_shot(db, session_id, Random(42))
        assert next_coordinate != coordinate
    async with sessions() as db:
        shots = list(await db.scalars(select(Shot).order_by(Shot.sequence)))
        assert [shot.result for shot in shots] == ["hit", None]


async def test_rejected_operation_rolls_back(client, sessions):
    session_id = UUID((await client.post("/game")).json()["session_id"])
    async with sessions() as db:
        with pytest.raises(Conflict):
            await accept_shot_result(db, session_id, "hit")
        assert not db.in_transaction()
        assert await make_shot(db, session_id, Random(42))


async def test_database_rejects_duplicate_shot_and_rolls_back(client, sessions):
    session_id = UUID((await client.post("/game")).json()["session_id"])
    async with sessions() as db:
        with pytest.raises(IntegrityError):
            async with db.begin():
                game = await db.get(GameSession, session_id)
                add_shot(db, game, "incoming", "A1", "miss")
                add_shot(db, game, "incoming", "A1", "miss")
    async with sessions() as db:
        assert list(await db.scalars(select(Shot))) == []
        assert (await db.get(GameSession, session_id)).sequence == 0


async def test_database_rejects_orphan(sessions):
    async with sessions() as db:
        with pytest.raises(IntegrityError):
            async with db.begin():
                db.add(
                    Shot(
                        session_id=uuid4(),
                        sequence=1,
                        direction="incoming",
                        coordinate="A1",
                        result="miss",
                    )
                )


async def test_pending_shot_survives_application_restart(database_url, sessions):
    settings = Settings(database_url=database_url, db_connect_timeout=5.0, _env_file=None)
    first_app = create_app(settings)
    async with first_app.router.lifespan_context(first_app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=first_app), base_url="http://test"
        ) as client:
            session_id = (await client.post("/game")).json()["session_id"]
            target = (await client.post(f"/game/{session_id}/shot")).json()["coordinate"]

    second_app = create_app(settings)
    async with second_app.router.lifespan_context(second_app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=second_app), base_url="http://test"
        ) as client:
            response = await client.post(f"/game/{session_id}/shot/result", json={"result": "hit"})
            assert response.status_code == 200
            next_target = (await client.post(f"/game/{session_id}/shot")).json()["coordinate"]
            assert next_target != target
