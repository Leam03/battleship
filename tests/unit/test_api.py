from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from sqlalchemy.exc import OperationalError

from battleship.api.dependencies import get_db
from battleship.config import Settings
from battleship.db.models import SCHEMA_REVISION
from battleship.main import create_app


@pytest.fixture
def app():
    return create_app(Settings(_env_file=None))


async def test_lifespan_and_openapi(app):
    async with app.router.lifespan_context(app):
        assert app.state.sessions is not None
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            assert (await client.get("/health")).status_code == 200
            schema = (await client.get("/openapi.json")).json()
            assert len([p for p in schema["paths"] if p.startswith("/game")]) == 5
            assert "422" not in str(schema)
            assert (await client.get("/missing")).json() == {"detail": "Not Found"}
            assert (await client.get("/openapi.json")).status_code == 200


@pytest.mark.parametrize("mode", ["schema", "connection"])
async def test_readiness_failure(app, mode):
    db = AsyncMock()
    if mode == "schema":
        db.scalar.return_value = "old"
    else:
        db.scalar.side_effect = OperationalError("test", {}, Exception("offline"))
    app.dependency_overrides[get_db] = lambda: db
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/ready")
    assert response.status_code == 503
    assert isinstance(response.json()["detail"], str)


async def test_internal_error_does_not_leak_details(app, monkeypatch):
    monkeypatch.setattr(
        "battleship.services.game.create_game", AsyncMock(side_effect=RuntimeError("secret-dsn"))
    )
    app.dependency_overrides[get_db] = lambda: AsyncMock()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        response = await client.post("/game")
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}


async def test_database_dependency_opens_and_closes_session(app):
    db = AsyncMock()
    db.scalar.return_value = SCHEMA_REVISION

    def factory():
        return db

    db.__aenter__.return_value = db
    app.state.sessions = factory
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        assert (await client.get("/ready")).status_code == 200
    db.__aexit__.assert_awaited_once()


async def test_invalid_uuid_maps_to_404(app):
    app.dependency_overrides[get_db] = lambda: AsyncMock()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        assert (await client.post("/game/broken/close")).status_code == 404
        assert (
            await client.post(f"/game/{uuid4()}/opponent-shot", json={"coordinate": ""})
        ).status_code == 400


async def test_method_not_allowed_preserves_allow_header(app):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/game")
    assert response.status_code == 405
    assert response.json() == {"detail": "Method Not Allowed"}
    assert response.headers["allow"] == "POST"


async def test_browser_page_assets_and_random_fleet(app):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        page = await client.get("/")
        assert page.status_code == 200
        assert 'lang="ru"' in page.text
        for asset in ("app.js", "style.css"):
            assert (await client.get(f"/static/{asset}")).status_code == 200
        fleet = (await client.get("/play/fleet")).json()
        assert len(fleet["ships"]) == 10
