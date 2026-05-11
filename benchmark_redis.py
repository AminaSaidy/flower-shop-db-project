"""
benchmark_redis.py — Redis Cache Benchmark
==========================================
Measures GET /api/products/ latency with and without Redis cache.
Runs inside the container to eliminate docker compose exec overhead (~10-15ms).

Usage:
    docker compose exec api_1 python benchmark_redis.py

Prerequisites:
    1. docker compose up -d
    2. docker compose run --rm api_1 alembic upgrade head
    3. docker compose exec api_1 python seed.py
    4. Add 500 products via docs/benchmarks/benchmark_data_gen.sql
"""

import asyncio
import time
import httpx
import redis.asyncio as aioredis
from app.core.config import settings


async def main():
    redis = aioredis.from_url(settings.REDIS_URL)
    cache_key = "products:None:None:None"
    times_db, times_cache = [], []

    async with httpx.AsyncClient() as client:
        print("DB hit measurements (5 runs, cache cleared before each):")
        for i in range(5):
            await redis.delete(cache_key)
            start = time.perf_counter()
            await client.get("http://127.0.0.1:8000/api/products/")
            elapsed = (time.perf_counter() - start) * 1000
            times_db.append(elapsed)
            print(f"  Run #{i+1}: {elapsed:.2f}ms")

        await client.get("http://127.0.0.1:8000/api/products/")  # warm up

        print("\nCache hit measurements (5 runs):")
        for i in range(5):
            start = time.perf_counter()
            await client.get("http://127.0.0.1:8000/api/products/")
            elapsed = (time.perf_counter() - start) * 1000
            times_cache.append(elapsed)
            print(f"  Run #{i+1}: {elapsed:.2f}ms")

    avg_db = sum(times_db) / len(times_db)
    avg_cache = sum(times_cache) / len(times_cache)

    print(f"\nDB hit avg:    {avg_db:.2f}ms")
    print(f"Cache hit avg: {avg_cache:.2f}ms")
    print(f"Improvement:   ~{avg_db/avg_cache:.1f}x faster")

    await redis.aclose()


if __name__ == "__main__":
    asyncio.run(main())