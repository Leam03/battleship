import asyncio
import csv
import json
from dataclasses import asdict, dataclass
from itertools import combinations
from pathlib import Path

import httpx

from battleship.arena.match import play_match
from battleship.arena.models import MatchResult, Player


@dataclass
class Standing:
    name: str
    played: int = 0
    wins: int = 0
    losses: int = 0
    technical_failures: int = 0
    unscored: int = 0
    rank: int = 0


def build_schedule(players: list[Player], games_per_pair: int) -> list[tuple[Player, Player]]:
    if len(players) < 2 or len({p.name for p in players}) != len(players):
        raise ValueError("Provide at least two players with distinct names")
    if games_per_pair < 2 or games_per_pair % 2:
        raise ValueError("Games per pair must be a positive even number")
    return [
        (left, right) if game % 2 == 0 else (right, left)
        for left, right in combinations(players, 2)
        for game in range(games_per_pair)
    ]


def build_standings(players: list[Player], matches: list[MatchResult]) -> list[Standing]:
    table = {player.name: Standing(player.name) for player in players}
    for match in matches:
        for name in match.players:
            row = table[name]
            row.played += 1
            row.technical_failures += int(name in match.failures)
            if match.winner is None:
                row.unscored += 1
            elif name == match.winner:
                row.wins += 1
            else:
                row.losses += 1
    result = sorted(table.values(), key=lambda row: (-row.wins, row.name))
    for index, row in enumerate(result):
        row.rank = (
            result[index - 1].rank if index and row.wins == result[index - 1].wins else index + 1
        )
    return result


async def run_tournament(
    players: list[Player], games_per_pair: int = 2, concurrency: int = 4
) -> list[MatchResult]:
    schedule = build_schedule(players, games_per_pair)
    if concurrency < 1:
        raise ValueError("Concurrency must be positive")
    semaphore = asyncio.Semaphore(concurrency)
    async with httpx.AsyncClient(
        limits=httpx.Limits(max_connections=concurrency * 2), trust_env=False
    ) as http:

        async def play(pair: tuple[Player, Player]) -> MatchResult:
            async with semaphore:
                return await play_match(*pair, http)

        return list(await asyncio.gather(*(play(pair) for pair in schedule)))


def write_results(directory: Path, players: list[Player], matches: list[MatchResult]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    standings = build_standings(players, matches)
    data = {"matches": [asdict(m) for m in matches], "standings": [asdict(s) for s in standings]}
    (directory / "results.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with (directory / "standings.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(asdict(standings[0])))
        writer.writeheader()
        for row in standings:
            values = asdict(row)
            if row.name.lstrip().startswith(("=", "+", "-", "@")):
                values["name"] = "'" + row.name
            writer.writerow(values)
