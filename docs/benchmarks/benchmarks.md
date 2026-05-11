# Query Performance Benchmarks (R6)

## Methodology

All measurements were taken using PostgreSQL `EXPLAIN (ANALYZE, BUFFERS)` inside a Docker container
on a local development machine.

### Data Generation

The default `seed.py` script creates only 1 admin user, 4 categories, and 8 products — insufficient
for a meaningful index benchmark, as all orders would belong to a single user, making the composite
index on `(user_id, status)` ineffective (low selectivity on `user_id`).

To produce a realistic dataset, the following steps were taken:

**Step 1 — Load base seed data:**
```bash
docker compose exec api_1 python seed.py
```

**Step 2 — Generate 500 additional users via psql:**
```sql
INSERT INTO users (id, email, password_hash, full_name, role)
SELECT
    gen_random_uuid(),
    'user' || i || '@test.com',
    'hash',
    'Test User ' || i,
    'customer'
FROM generate_series(1, 500) AS i;
```

**Step 3 — Generate 50,000 orders distributed evenly across all 500 users (100 orders each):**
```sql
INSERT INTO orders (id, user_id, status, delivery_address, total_price)
SELECT
    gen_random_uuid(),
    u.id,
    (ARRAY['pending','confirmed','preparing','delivering','delivered','cancelled'])[floor(random()*6+1)],
    'Address ' || s.i,
    round((random() * 180 + 20)::numeric, 2)
FROM generate_series(1, 50000) AS s(i)
JOIN users u ON u.email = 'user' || (1 + (s.i % 500)) || '@test.com';
```

Note: the `JOIN` on email ensures each user receives exactly 100 orders. An earlier attempt using
`(SELECT id FROM users ORDER BY random() LIMIT 1)` as a subquery assigned all 50,000 orders to
a single user, as PostgreSQL evaluates such subqueries once per statement rather than per row.

**Final dataset:** 501 users, 50,000 orders — 100 orders per user, statuses distributed randomly.

Migration **001** creates the base schema with single-column indexes:
- `ix_orders_user_id` — on `orders.user_id`
- `ix_orders_status` — on `orders.status`
- `ix_orders_created_at` — on `orders.created_at`

Migration **002** adds composite and additional performance indexes:
- `ix_orders_user_status` — composite on `(user_id, status)` ← key index for Test 1
- `ix_products_occasion` — on `products.occasion`
- `ix_products_color` — on `products.color`
- `ix_products_category_active` — composite on `(category_id, is_active)`

---

## Test 1 — Composite Index on Orders (PostgreSQL)

**Query:**
```sql
SELECT * FROM orders
WHERE user_id = '00097f92-b5bd-464d-9e78-cb6737fd653d'
AND status = 'pending';
```

### Before — Migration 001 (no composite index)

PostgreSQL used **two separate indexes** and intersected the results in memory (`BitmapAnd`):

```
Bitmap Heap Scan on orders
  (actual time=1.782..1.876 rows=18 loops=1)
  ->  BitmapAnd
        ->  Bitmap Index Scan on ix_orders_user_id
              Index Cond: (user_id = '...')
              (actual rows=100)
        ->  Bitmap Index Scan on ix_orders_status
              Index Cond: (status = 'pending')
              (actual rows=8270)
Planning Time: 1.815 ms
Execution Time: 2.224 ms
```

### After — Migration 002 (with composite index ix_orders_user_status)

PostgreSQL switched to a **single composite index scan** — no intersection needed:

```
Bitmap Heap Scan on orders
  (actual time=0.131..0.337 rows=18 loops=1)
  ->  Bitmap Index Scan on ix_orders_user_status
        Index Cond: ((user_id = '...') AND (status = 'pending'))
        (actual rows=18)
Planning Time: 5.089 ms
Execution Time: 0.542 ms
```

### Results

| State | Query Plan | Execution Time |
|---|---|---|
| Before (migration 001) | `BitmapAnd` (ix_orders_user_id + ix_orders_status) | 2.224 ms |
| After (migration 002) | `Bitmap Index Scan on ix_orders_user_status` | 0.542 ms |
| **Improvement** | | **~4x faster** |

### Analysis

Without the composite index, PostgreSQL scanned two separate indexes and intersected ~100 and ~8,270
rows in memory to find the 18 matching rows. With the composite index `(user_id, status)`,
PostgreSQL performs a single precise lookup — jumping directly to the 18 rows satisfying both
conditions.

The improvement factor of **~4x** was measured on a local machine with data in shared buffers
(warm cache). On a production server with a cold cache and larger dataset, the improvement is
expected to be **10–30x**, as disk I/O costs would dominate and the composite index minimizes
the number of pages read.

### How to Reproduce

```bash
# Apply base migrations (001 only)
docker compose run --rm api_1 alembic downgrade 001

# Verify indexes
docker compose exec postgres psql -U flower_user -d flower_shop \
  -c "SELECT indexname FROM pg_indexes WHERE tablename = 'orders' ORDER BY indexname;"

# Run EXPLAIN ANALYZE in psql
docker compose exec postgres psql -U flower_user -d flower_shop

# Then in psql:
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM orders
WHERE user_id = '00097f92-b5bd-464d-9e78-cb6737fd653d'
AND status = 'pending';

# Apply migration 002 and repeat
docker compose run --rm api_1 alembic upgrade head
```

---

## Test 2 — Redis Cache on Catalog Endpoint

**Endpoint:** `GET /api/products/`

### Data Generation

The default `seed.py` creates only 8 products — insufficient for a meaningful cache benchmark,
as PostgreSQL returns them near-instantly regardless of caching. To produce a realistic dataset,
500 additional products were generated via psql:

```sql
INSERT INTO products (id, category_id, name, slug, price, stock_quantity, occasion, color, is_active)
SELECT
    gen_random_uuid(),
    (SELECT id FROM categories ORDER BY random() LIMIT 1),
    'Product ' || i,
    'product-' || i,
    round((random() * 200 + 10)::numeric, 2),
    floor(random() * 100)::int,
    (ARRAY['birthday','wedding','anniversary','any'])[floor(random()*4+1)],
    (ARRAY['red','white','pink','yellow','purple','orange','green'])[floor(random()*7+1)],
    true
FROM generate_series(1, 500) AS i;
```

**Final dataset:** 508 products total (500 generated + 8 from seed).

### How the Cache Works

```python
cache_key = f"products:{category}:{occasion}:{color}"

cached = await r.get(cache_key)
if cached:
    return json.loads(cached)   # Redis hit, DB not touched

# DB hit — fetch from PostgreSQL, store in Redis with TTL 60s
await r.set(cache_key, json.dumps(response), ex=60)
```

- **Cache miss** (first request): query goes to PostgreSQL → result stored in Redis (TTL 60s)
- **Cache hit** (subsequent requests): result returned directly from Redis, PostgreSQL not queried

### Measurement Methodology

Initial measurements using `docker compose exec api_1 curl` showed ~10–15ms overhead per call
from the exec mechanism itself, obscuring the true difference. Final measurements were taken
using a Python script executed **inside** the container to eliminate this overhead:

```python
import asyncio, httpx, time
import redis.asyncio as aioredis

async def benchmark():
    async with httpx.AsyncClient() as client:
        times_db, times_cache = [], []

        for _ in range(5):
            start = time.perf_counter()
            await client.get('http://localhost:8000/api/products/')
            times_db.append((time.perf_counter() - start) * 1000)
            red = aioredis.from_url('redis://redis:6379/0')
            await red.delete('products:None:None:None')

        await client.get('http://localhost:8000/api/products/')

        for _ in range(5):
            start = time.perf_counter()
            await client.get('http://localhost:8000/api/products/')
            times_cache.append((time.perf_counter() - start) * 1000)

        print(f'DB hit avg: {sum(times_db)/len(times_db):.2f}ms')
        print(f'Cache hit avg: {sum(times_cache)/len(times_cache):.2f}ms')
        print(f'Improvement: {sum(times_db)/len(times_db)/(sum(times_cache)/len(times_cache)):.1f}x')

asyncio.run(benchmark())
```

### Results

Measured after `docker compose restart postgres` to simulate cold cache conditions.

**Individual runs:**

| Run | DB hit (cold→warm) | Cache hit |
|---|---|---|
| #1 | 2616.52 ms | 34.73 ms |
| #2 | 169.80 ms | 41.24 ms |
| #3 | 32.56 ms | 34.66 ms |
| #4 | 43.90 ms | 30.86 ms |
| #5 | 47.26 ms | 34.75 ms |
| **avg** | **582.01 ms** | **35.25 ms** |

**By scenario:**

| Scenario | DB hit | Cache hit | Improvement |
|---|---|---|---|
| Cold cache (run #1, after postgres restart) | 2616 ms | 35 ms | **~74x** |
| Warm cache (runs #2–5, steady state) | ~73 ms | 35 ms | **~2x** |
| **Overall average** | **582 ms** | **35 ms** | **~16.5x** |

### Analysis

The benchmark reveals two distinct scenarios:

**Cold cache** (first request after PostgreSQL restart): PostgreSQL reads all 508 product rows
from disk — 2616ms. Redis returns the cached JSON in 35ms — **~74x improvement**. This scenario
is realistic in production after deployments or server restarts.

**Warm cache** (subsequent requests): PostgreSQL data is loaded into shared buffers — response
time drops to ~73ms. Redis remains at ~35ms — **~2x improvement**. Even with a warm PostgreSQL
cache, Redis wins because it skips query parsing, planning, and execution entirely.

Initial measurements using `docker compose exec api_1 curl` showed inflated times due to
~10–15ms exec overhead per call. Final measurements use `benchmark_redis.py` running inside
the container for accurate results.

The 60-second TTL balances data freshness (product catalog changes infrequently) against cache
efficiency. Cache invalidation on product updates is a recommended future improvement.

### How to Reproduce

```bash
# Restart postgres to simulate cold cache
docker compose restart postgres

# Wait for postgres to be healthy
docker compose ps postgres

# Run benchmark inside container (eliminates docker exec overhead)
docker compose exec api_1 python benchmark_redis.py
```

---

## Summary

| Test | Before | After | Improvement |
|---|---|---|---|
| PostgreSQL composite index (`ix_orders_user_status`) | 2.224 ms (BitmapAnd) | 0.542 ms (Index Scan) | **~4x** |
| Redis cache — cold PostgreSQL (after restart) | 2616 ms | 35 ms | **~74x** |
| Redis cache — warm PostgreSQL (steady state) | 73 ms | 35 ms | **~2x** |
| Redis cache — overall average | 582 ms | 35 ms | **~16.5x** |