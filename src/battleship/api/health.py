from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from battleship.api.dependencies import Database
from battleship.db.models import SCHEMA_REVISION

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready(db: Database) -> dict[str, str]:
    try:
        revision = await db.scalar(text("SELECT version_num FROM alembic_version"))
        if revision != SCHEMA_REVISION:
            raise HTTPException(503, "Database schema is not ready")
        await db.execute(text("SELECT id FROM game_sessions LIMIT 0"))
    except (SQLAlchemyError, OSError, TimeoutError) as exc:
        raise HTTPException(503, "Database is not ready") from exc
    return {"status": "ready"}
