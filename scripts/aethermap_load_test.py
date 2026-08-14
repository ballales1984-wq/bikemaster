"""AetherMap load test (Sprint 4 — task 6.19).

Simula 1000 richieste concorrenti a `/api/v1/rides/{ride_id}/terrain`
e raccoglie statistiche P50/P95/P99.

Uso:
    python scripts/aethermap_load_test.py --base-url http://localhost:8001 --ride-id 1 --concurrency 50
"""
from __future__ import annotations

import argparse
import asyncio
import statistics
import time
from typing import Any

try:
    import httpx
except ImportError:
    raise SystemExit("httpx required: pip install httpx") from None


async def _fire(client: httpx.AsyncClient, url: str, semaphore: asyncio.Semaphore) -> float:
    async with semaphore:
        t0 = time.perf_counter()
        try:
            resp = await client.get(url, timeout=30.0)
            resp.raise_for_status()
            return time.perf_counter() - t0
        except Exception as exc:
            print(f"ERROR: {exc}")
            return -1.0


async def run(base_url: str, ride_id: int, concurrency: int, total: int) -> dict[str, Any]:
    semaphore = asyncio.Semaphore(concurrency)
    url = f"{base_url}/api/v1/rides/{ride_id}/terrain?enabled=true"
    async with httpx.AsyncClient() as client:
        tasks = [_fire(client, url, semaphore) for _ in range(total)]
        durations = await asyncio.gather(*tasks)

    success = [d for d in durations if d >= 0.0]
    errors = total - len(success)
    if not success:
        return {"total": total, "errors": errors, "error_rate": 1.0}

    p50 = statistics.median(success)
    p95 = sorted(success)[int(len(success) * 0.95)]
    p99 = sorted(success)[int(len(success) * 0.99)]
    return {
        "total": total,
        "success": len(success),
        "errors": errors,
        "error_rate": errors / total,
        "p50_s": round(p50, 4),
        "p95_s": round(p95, 4),
        "p99_s": round(p99, 4),
        "max_s": round(max(success), 4),
        "min_s": round(min(success), 4),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="AetherMap terrain enrichment load test")
    parser.add_argument("--base-url", default="http://localhost:8001")
    parser.add_argument("--ride-id", type=int, default=1)
    parser.add_argument("--concurrency", type=int, default=50)
    parser.add_argument("--total", type=int, default=1000)
    args = parser.parse_args()

    print(f"Running {args.total} requests against {args.base_url} (concurrency={args.concurrency})")
    t0 = time.perf_counter()
    stats = asyncio.run(run(args.base_url, args.ride_id, args.concurrency, args.total))
    wall = time.perf_counter() - t0
    print(f"Wall time: {wall:.2f}s")
    for k, v in stats.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
