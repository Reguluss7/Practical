from __future__ import annotations

import argparse
import statistics
import time

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure /rooms/available latency and DB queries")
    parser.add_argument("--url", default="http://localhost:5080")
    parser.add_argument("--count", type=int, default=1000)
    parser.add_argument("--check-in", default="2026-11-12")
    parser.add_argument("--check-out", default="2026-11-14")
    args = parser.parse_args()

    with httpx.Client(base_url=args.url, timeout=10.0) as client:
        before = client.get("/stats").json()

        latencies_ms: list[float] = []
        t_start = time.perf_counter()
        for _ in range(args.count):
            t0 = time.perf_counter()
            resp = client.get(
                "/rooms/available",
                params={"check_in": args.check_in, "check_out": args.check_out},
            )
            resp.raise_for_status()
            latencies_ms.append((time.perf_counter() - t0) * 1000.0)
        total_sec = time.perf_counter() - t_start

        after = client.get("/stats").json()

    latencies_ms.sort()
    avg_ms = statistics.mean(latencies_ms)
    p95_idx = min(len(latencies_ms) - 1, int(len(latencies_ms) * 0.95))
    p95_ms = latencies_ms[p95_idx]

    db_delta = after["db_queries"] - before["db_queries"]
    hits_delta = after["cache_hits"] - before["cache_hits"]
    misses_delta = after["cache_misses"] - before["cache_misses"]

    print(f"Requests:     {args.count} ({args.check_in}..{args.check_out})")
    print(f"Total time:   {total_sec:.2f} s")
    print(f"Average:      {avg_ms:.2f} ms")
    print(f"p95:          {p95_ms:.2f} ms")
    print(f"DB queries:   {db_delta} (before={before['db_queries']}, after={after['db_queries']})")
    print(f"Cache hits:   {hits_delta} | misses: {misses_delta} | version: {after['cache_version']}")


if __name__ == "__main__":
    main()