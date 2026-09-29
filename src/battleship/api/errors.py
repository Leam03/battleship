import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from battleship.domain.errors import (
    AlreadyClosed,
    Conflict,
    GameError,
    InvalidInput,
    SessionClosed,
    SessionNotFound,
)

logger = logging.getLogger(__name__)
STATUS = {
    InvalidInput: 400,
    AlreadyClosed: 400,
    SessionNotFound: 404,
    Conflict: 409,
    SessionClosed: 410,
}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(GameError)
    async def game_error(request: Request, exc: GameError) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=STATUS.get(type(exc), 500))

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        if any(error["loc"][0] == "path" for error in exc.errors()):
            return JSONResponse({"detail": "Session not found"}, status_code=404)
        return JSONResponse({"detail": "Invalid request body"}, status_code=400)

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            {"detail": str(exc.detail)}, status_code=exc.status_code, headers=exc.headers
        )

    @app.exception_handler(Exception)
    async def internal_error(request: Request, exc: Exception) -> JSONResponse:
        logger.error("Unhandled error on %s", request.url.path, exc_info=exc)
        return JSONResponse({"detail": "Internal server error"}, status_code=500)
