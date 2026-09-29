import asyncio
import json
from time import perf_counter
from typing import Any
from uuid import UUID

import httpx
from pydantic import BaseModel, ValidationError

from battleship.api.schemas import Accepted, Closed, GameCreated, ShotCoordinate, ShotOutcome
from battleship.arena.models import Player, RequestTiming, TechnicalDefeat

MAX_RESPONSE_BYTES = 65_536


class GameClient:
    def __init__(
        self,
        player: Player,
        http: httpx.AsyncClient,
        timings: list[RequestTiming],
        timeout: float = 1.0,
    ) -> None:
        self.player = player
        self.http = http
        self.timings = timings
        self.timeout = timeout
        self.session_id: UUID | None = None

    async def request[T: BaseModel](
        self, operation: str, model: type[T], body: dict[str, str] | None = None
    ) -> T:
        path = "/game" if operation == "start" else f"/game/{self.session_id}/{operation}"
        expected_status = 201 if operation == "start" else 200
        started = perf_counter()
        elapsed = 0.0
        success = False
        try:
            async with asyncio.timeout(self.timeout):
                async with self.http.stream(
                    "POST",
                    f"{self.player.url}{path}",
                    json=body,
                    follow_redirects=False,
                    timeout=self.timeout,
                ) as response:
                    content = bytearray()
                    async for chunk in response.aiter_bytes():
                        content.extend(chunk)
                        if len(content) > MAX_RESPONSE_BYTES:
                            raise TechnicalDefeat(self.player.name, "Response is too large")
                    elapsed = perf_counter() - started
                    if elapsed > self.timeout:
                        raise TimeoutError
                    if response.status_code != expected_status:
                        raise TechnicalDefeat(
                            self.player.name, f"{operation}: unexpected HTTP {response.status_code}"
                        )
            payload: Any = json.loads(content)
            if operation == "start" and isinstance(payload, dict):
                # Keep a valid ID for cleanup even if the fleet response is malformed.
                candidate = payload.get("session_id")
                if isinstance(candidate, str):
                    try:
                        self.session_id = UUID(candidate)
                    except ValueError:
                        pass
            parsed = model.model_validate(payload)
            success = True
            return parsed
        except (TimeoutError, httpx.TimeoutException) as exc:
            raise TechnicalDefeat(self.player.name, f"{operation}: deadline exceeded") from exc
        except httpx.HTTPError as exc:
            raise TechnicalDefeat(self.player.name, f"{operation}: transport error") from exc
        except (ValueError, ValidationError, RecursionError) as exc:
            raise TechnicalDefeat(self.player.name, f"{operation}: invalid response") from exc
        finally:
            self.timings.append(
                RequestTiming(
                    self.player.name, operation, elapsed or perf_counter() - started, success
                )
            )

    async def start(self) -> GameCreated:
        return await self.request("start", GameCreated)

    async def shot(self) -> str:
        return (await self.request("shot", ShotCoordinate)).coordinate

    async def defend(self, coordinate: str) -> ShotOutcome:
        return await self.request("opponent-shot", ShotOutcome, {"coordinate": coordinate})

    async def report(self, result: str) -> None:
        await self.request("shot/result", Accepted, {"result": result})

    async def close(self) -> None:
        if self.session_id is not None:
            await self.request("close", Closed)
