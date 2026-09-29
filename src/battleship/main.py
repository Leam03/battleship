import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import async_sessionmaker

from battleship.api import games, health, play
from battleship.api.errors import register_error_handlers
from battleship.config import Settings, get_settings
from battleship.db.session import create_engine
from battleship.logging import RequestLogging


class BattleshipAPI(FastAPI):
    def openapi(self) -> dict[str, Any]:
        if self.openapi_schema is None:
            schema = get_openapi(title=self.title, version=self.version, routes=self.routes)
            for path in schema["paths"].values():
                for operation in path.values():
                    operation.get("responses", {}).pop("422", None)
            self.openapi_schema = schema
        return self.openapi_schema


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        logging.basicConfig(
            level=settings.log_level, format="%(asctime)s %(levelname)s %(message)s"
        )
        engine = create_engine(settings)
        app.state.sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            yield
        finally:
            await engine.dispose()

    app = BattleshipAPI(title="Battleship", version="1.0.0", lifespan=lifespan)
    app.include_router(games.router)
    app.include_router(health.router)
    app.include_router(play.router)
    app.mount("/static", StaticFiles(directory=play.STATIC_DIRECTORY), name="static")
    app.add_middleware(RequestLogging)
    register_error_handlers(app)

    return app


app = create_app()
