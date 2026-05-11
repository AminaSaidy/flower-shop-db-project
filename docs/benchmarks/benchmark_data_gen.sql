-- TEST 1: PostgreSQL Composite Index Benchmark
-- Goal: demonstrate ix_orders_user_status (migration 002)
--       vs single-column indexes (migration 001)

-- Step 1: Generate 500 test users
-- (requires base seed.py to be run first: docker compose exec api_1 python seed.py)
INSERT INTO users (id, email, password_hash, full_name, role)
SELECT
    gen_random_uuid(),
    'user' || i || '@test.com',
    'hash',
    'Test User ' || i,
    'customer'
FROM generate_series(1, 500) AS i;

-- Step 2: Generate 50,000 orders distributed evenly across all 500 users
-- Each user receives exactly 100 orders (100 orders * 500 users = 50,000 total)
INSERT INTO orders (id, user_id, status, delivery_address, total_price)
SELECT
    gen_random_uuid(),
    u.id,
    (ARRAY['pending','confirmed','preparing','delivering','delivered','cancelled'])[floor(random()*6+1)],
    'Address ' || s.i,
    round((random() * 180 + 20)::numeric, 2)
FROM generate_series(1, 50000) AS s(i)
JOIN users u ON u.email = 'user' || (1 + (s.i % 500)) || '@test.com';

-- Step 3: Verify distribution (each user should have exactly 100 orders)
SELECT user_id, count(*)
FROM orders
GROUP BY user_id
ORDER BY count(*) DESC
LIMIT 5;

-- benchmark query — run before and after migration 002

-- Run BEFORE (migration 001 — no composite index):
-- docker compose run --rm api_1 alembic downgrade 001
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM orders
WHERE user_id = '00097f92-b5bd-464d-9e78-cb6737fd653d'
AND status = 'pending';
-- Expected plan: BitmapAnd (ix_orders_user_id + ix_orders_status)
-- Expected time: ~2ms

-- Run AFTER (migration 002 — composite index ix_orders_user_status):
-- docker compose run --rm api_1 alembic upgrade head
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM orders
WHERE user_id = '00097f92-b5bd-464d-9e78-cb6737fd653d'
AND status = 'pending';
-- Expected plan: Bitmap Index Scan on ix_orders_user_status
-- Expected time: ~0.5ms


-- TEST 2: Redis Cache Benchmark
-- Goal: demonstrate caching effect on GET /api/products/

-- Generate 500 products for a realistic catalog size
-- (8 default products from seed.py are insufficient for meaningful benchmark)
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

-- Verify total product count
SELECT count(*) FROM products WHERE is_active = true;
-- Expected: 508 (500 generated + 8 from seed.py)