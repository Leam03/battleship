from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from battleship.config import Settings


def create_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_pre_ping=True,
        connect_args={
            "timeout": settings.db_connect_timeout,
            "command_timeout": settings.db_statement_timeout_ms / 1000,
            "server_settings": {
                "statement_timeout": str(settings.db_statement_timeout_ms),
                "lock_timeout": str(settings.db_lock_timeout_ms),
            },
        },
        hide_parameters=True,
    )
