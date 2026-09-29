from collections.abc import AsyncIterator
from random import Random
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.sessions() as session:
        yield session


def get_rng() -> Random:
    return Random()


Database = Annotated[AsyncSession, Depends(get_db)]
RandomSource = Annotated[Random, Depends(get_rng)]
