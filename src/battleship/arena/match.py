import asyncio

import httpx

from battleship.arena.client import GameClient
from battleship.arena.models import MatchResult, Move, Player, TechnicalDefeat
from battleship.arena.referee import RefereeBoard


async def close_sessions(clients: list[GameClient], match: MatchResult) -> None:
    async def close(client: GameClient) -> None:
        try:
            await client.close()
        except TechnicalDefeat as exc:
            match.add_failure(exc.player, exc.reason)

    await asyncio.gather(*(close(client) for client in clients))


async def play_match(
    first: Player, second: Player, http: httpx.AsyncClient, request_deadline: float = 1.0
) -> MatchResult:
    if first.name == second.name:
        raise ValueError("Players must have distinct names")
    match = MatchResult((first.name, second.name), first.name)
    clients = [
        GameClient(player, http, match.timings, request_deadline) for player in (first, second)
    ]
    boards: list[RefereeBoard] = []
    fired: list[set[str]] = [set(), set()]
    try:
        for client in clients:
            try:
                boards.append(RefereeBoard.from_start(client.player.name, await client.start()))
            except TechnicalDefeat as exc:
                match.add_failure(exc.player, exc.reason)
        if not match.failures:
            turn = 0
            while len(match.moves) < 200:
                attacker, defender = clients[turn], clients[1 - turn]
                coordinate = await attacker.shot()
                if coordinate in fired[turn]:
                    raise TechnicalDefeat(attacker.player.name, f"Repeated shot: {coordinate}")
                fired[turn].add(coordinate)
                result = (await defender.defend(coordinate)).result
                boards[1 - turn].check_result(coordinate, result)
                await attacker.report(result)
                match.moves.append(Move(attacker.player.name, coordinate, result))
                if boards[1 - turn].has_won():
                    match.winner = attacker.player.name
                    match.reason = "All 20 enemy ship cells were hit"
                    break
                if result == "miss":
                    turn = 1 - turn
    except TechnicalDefeat as exc:
        match.add_failure(exc.player, exc.reason)
    finally:
        await close_sessions(clients, match)
    match.settle()
    return match
