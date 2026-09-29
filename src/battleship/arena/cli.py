import argparse
import asyncio
import json
from pathlib import Path

import httpx
from pydantic import TypeAdapter

from battleship.arena.match import play_match
from battleship.arena.models import MatchResult, Player
from battleship.arena.tournament import build_standings, run_tournament, write_results


async def single_match(players: list[Player]) -> list[MatchResult]:
    async with httpx.AsyncClient(trust_env=False) as http:
        return [await play_match(players[0], players[1], http)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Арена Морского боя")
    parser.add_argument("--output", type=Path, default=Path("results"))
    commands = parser.add_subparsers(dest="command", required=True)
    match = commands.add_parser("match", help="Матч двух сервисов")
    match.add_argument("first_url")
    match.add_argument("second_url")
    tournament = commands.add_parser("tournament", help="Круговой турнир")
    tournament.add_argument("players", type=Path)
    tournament.add_argument("--games-per-pair", type=int, default=2)
    tournament.add_argument("--concurrency", type=int, default=4)
    args = parser.parse_args()
    try:
        if args.command == "match":
            players = [
                Player(name="first", url=args.first_url),
                Player(name="second", url=args.second_url),
            ]
            matches = asyncio.run(single_match(players))
        else:
            players = TypeAdapter(list[Player]).validate_json(
                args.players.read_text(encoding="utf-8")
            )
            matches = asyncio.run(run_tournament(players, args.games_per_pair, args.concurrency))
        write_results(args.output, players, matches)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(
        json.dumps(
            [vars(row) for row in build_standings(players, matches)], ensure_ascii=False, indent=2
        )
    )
