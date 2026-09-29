import asyncio
import json
import math
import os
import platform
from pathlib import Path
from time import perf_counter

import httpx
import pytest

from battleship.arena.match import play_match
from battleship.arena.models import Player


@pytest.mark.parametrize("concurrency", [10, 25])
async def test_parallel_match_latency(concurrency):
    first = Player(name="first", url=os.environ["BATTLESHIP_FIRST_URL"])
    second = Player(name="second", url=os.environ["BATTLESHIP_SECOND_URL"])
    async with httpx.AsyncClient(
        limits=httpx.Limits(max_connections=concurrency * 2), trust_env=False
    ) as client:
        started = perf_counter()
        matches = await asyncio.gather(
            *(play_match(first, second, client) for _ in range(concurrency))
        )
        duration = perf_counter() - started
    timings = [t for match in matches for t in match.timings]
    values = sorted(t.elapsed for t in timings)

    def percentile(p):
        return values[max(0, math.ceil(len(values) * p) - 1)]

    report = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "logical_cpus": os.cpu_count(),
        "processor": platform.processor(),
        "concurrency": concurrency,
        "duration_seconds": duration,
        "requests": len(timings),
        "failed_requests": sum(not t.success for t in timings),
        "p50": percentile(0.50),
        "p95": percentile(0.95),
        "p99": percentile(0.99),
        "max": values[-1],
        "match_failures": [m.failures for m in matches if m.failures],
        "operations": sorted({t.operation for t in timings}),
    }
    directory = Path("results")
    await asyncio.to_thread(directory.mkdir, exist_ok=True)
    await asyncio.to_thread(
        (directory / f"performance-{concurrency}.json").write_text,
        json.dumps(report, indent=2),
        encoding="utf-8",
    )
    assert all(m.winner and not m.failures for m in matches), report
    assert all(t.success and t.elapsed < 1 for t in timings), report
