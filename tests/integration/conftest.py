import os
import subprocess
import sys

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker

from battleship.api.dependencies import get_db
from battleship.config import Settings
from battleship.db.session import create_engine
from battleship.main import create_app


@pytest.fixture(scope="session")
def database_url():
    url = os.environ["TEST_DATABASE_URL"]
    database = make_url(url).database or ""
    if not database.endswith("_test"):
        pytest.fail("TEST_DATABASE_URL must name a dedicated database ending in _test")
    return url


@pytest.fixture(scope="session", autouse=True)
def migrated_database(database_url):
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        env={**os.environ, "DATABASE_URL": database_url},
        check=True,
    )


@pytest.fixture
async def sessions(database_url):
    settings = Settings(database_url=database_url, db_connect_timeout=5.0, _env_file=None)
    engine = create_engine(settings)
    async with engine.begin() as connection:
        await connection.execute(
            text("TRUNCATE shots, game_sessions, browser_games RESTART IDENTITY")
        )
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
async def client(sessions, database_url):
    app = create_app(Settings(database_url=database_url, _env_file=None))

    async def db():
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_db] = db
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as http:
        yield http
