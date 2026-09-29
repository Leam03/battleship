import asyncio
import json
from uuid import uuid4

import httpx

from battleship.domain.fleet import FALLBACK


class FakeServices:
    def __init__(self, faults=None, water_first=False):
        self.faults = faults or {}
        self.games = {}
        self.closed = set()
        self.water_first = water_first

    async def __call__(self, request):
        name = request.url.host
        operation = request.url.path.split("/")[-1]
        fault = self.faults.get(name)
        if fault == "slow" and operation != "close":
            await asyncio.sleep(0.05)
        if fault == "network" and operation != "close":
            raise httpx.ConnectError("offline", request=request)
        if operation == "game":
            session_id = str(uuid4())
            self.games[session_id] = {"received": set(), "fired": [], "reports": []}
            ships = [{"coordinates": list(ship)} for ship in FALLBACK]
            if fault == "fleet":
                ships.pop()
            return httpx.Response(201, json={"session_id": session_id, "ships": ships})
        session_id = request.url.path.split("/")[2]
        game = self.games[session_id]
        if operation == "close":
            self.closed.add(session_id)
            return httpx.Response(500 if fault == "close" else 200, json={"status": "closed"})
        if operation == "shot":
            occupied = {c for ship in FALLBACK for c in ship}
            cells = [f"{x}{y}" for x in "ABCDEFGHIJ" for y in range(1, 11)]
            if self.water_first:
                cells.sort(key=lambda c: c in occupied)
            target = (
                cells[0] if fault == "repeat" else next(c for c in cells if c not in game["fired"])
            )
            game["fired"].append(target)
            return httpx.Response(200, json={"coordinate": target})
        body = json.loads(request.content)
        if operation == "result":
            game["reports"].append(body["result"])
            return httpx.Response(200, json={"status": "accepted"})
        coordinate = body["coordinate"]
        game["received"].add(coordinate)
        result = "miss"
        for ship in FALLBACK:
            if coordinate in ship:
                result = "killed" if set(ship) <= game["received"] else "hit"
        if fault == "lie":
            result = "miss" if result != "miss" else "hit"
        return httpx.Response(200, json={"result": result})
