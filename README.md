# Flower Shop

E-commerce platform for a flower shop with Telegram bot integration.
Built for Database Application and Design course, INHA University 2026.

The service exposes a FastAPI REST API, stores core data in PostgreSQL, uses Redis for carts and rate limiting, synchronizes products to Elasticsearch for search, and runs scheduled jobs with Celery.

## Stack

- FastAPI + Uvicorn
- PostgreSQL 16 + SQLAlchemy async + Alembic
- Redis 7 for cart storage, Celery broker/result backend, and rate limiting
- Elasticsearch 8 for product full-text search
- Celery worker + Celery Beat for background jobs
- Nginx as a reverse proxy and load balancer for two API replicas
- Prometheus metrics endpoint and Grafana container
- Telegram bot dependencies and settings are present for Web App integration

## Project Structure

```text
app/
  api/endpoints/      REST and WebSocket routes
  core/               config, JWT helpers, rate limiter, telemetry
  db/                 SQLAlchemy models and async session
  static/             browser frontend served by FastAPI
  services/           Elasticsearch synchronization/search
  worker/             Celery app and scheduled tasks
migrations/           Alembic migrations
docs/                 ER, relational, architecture, and BPMN diagrams
nginx/                Nginx reverse proxy config
observability/        Prometheus config
seed.py               Demo data loader
```

## Requirements

- Docker and Docker Compose
- Python 3.12, only if running parts of the app outside Docker

## Quick start

```bash
git clone git@github.com:AminaSaidy/flower-shop-db-project.git
cd flower-shop-db-project
cp .env.example .env
docker compose up -d --build
docker compose exec api_1 alembic upgrade head
docker compose exec api_1 python seed.py
```

**Deployed URL:** https://flower-uz.tech
**API Docs:** https://flower-uz.tech/api/docs

## Production

- Application domain: `https://flower-uz.tech`
- API docs: `https://flower-uz.tech/api/docs`
- ReDoc: `https://flower-uz.tech/api/redoc`
- Health check: `https://flower-uz.tech/health`

## Environment Variables

Copy the example file and adjust secrets before running the project:

```bash
cp .env.example .env
```

Main variables:

| Variable | Description | Example |
| --- | --- | --- |
| `POSTGRES_USER` | PostgreSQL user used by the container | `flower_user` |
| `POSTGRES_PASSWORD` | PostgreSQL password | `changeme` |
| `POSTGRES_DB` | PostgreSQL database name | `flower_shop` |
| `DATABASE_URL` | Async SQLAlchemy connection string | `postgresql+asyncpg://flower_user:changeme@postgres:5432/flower_shop` |
| `REDIS_URL` | Redis connection used by API | `redis://redis:6379/0` |
| `ES_URL` | Elasticsearch URL | `http://elasticsearch:9200` |
| `ES_INDEX` | Product search index name | `products` |
| `SECRET_KEY` | JWT signing key | generate with `openssl rand -hex 32` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT lifetime in minutes | `60` |
| `ENVIRONMENT` | Runtime environment name | `development` |
| `CELERY_BROKER_URL` | Celery broker Redis database | `redis://redis:6379/1` |
| `CELERY_RESULT_BACKEND` | Celery result backend Redis database | `redis://redis:6379/2` |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | token from BotFather |
| `TELEGRAM_WEB_APP_URL` | Public Telegram Web App URL | `https://flower-uz.tech` |

## Run Locally

Start all services:

```bash
docker compose up -d --build
```

Apply database migrations:

```bash
docker compose exec api_1 alembic upgrade head
```

Load demo data:

```bash
docker compose exec api_1 python seed.py
```

Useful local URLs:

- Frontend: `http://localhost/`
- API health check: `http://localhost/health`
- Swagger UI: `http://localhost/api/docs`
- ReDoc: `http://localhost/api/redoc`
- Prometheus metrics: `http://localhost/metrics`
- Grafana: `http://localhost:3000` with password `admin`

Stop services:

```bash
docker compose down
```

## Testing

The project uses `pytest` and `httpx` (`TestClient`) for API testing. To run the test suite, ensure your Docker containers are running, then execute:

```bash
docker compose exec -e PYTHONPATH=/app api_1 pytest
```

The tests cover:
- API endpoint validation and proper status codes (200, 404, 422, etc.)
- Authentication blocks and JWT validation
- Product catalog reading and filtering errors
- Proper JSON formatting

## Database

The current schema contains:

- `users`: customer/admin accounts
- `categories`: product categories
- `products`: catalog items with price, stock, occasion, color, and image URL
- `orders`: customer orders and delivery address
- `order_items`: products inside each order
- `cart_items`: cart data is stored in Redis at runtime, cart_items table is kept in schema for reference
- `reviews`: product reviews with rating constraints

Diagrams are stored in `docs/`:

- `docs/er-diagram.png`
- `docs/relational-schema.png`
- `docs/architecture.png`
- BPMN files and PNG exports in `docs/bpmn/`

## API Overview

Auth:

- `POST /api/auth/register` - create customer account and receive JWT
- `POST /api/auth/login` - sign in and receive JWT

Catalog:

- `GET /api/products/` - list active products, optionally filtered by `category`, `occasion`, and `color`
- `POST /api/products/` - create product, admin only
- `GET /api/products/search?q=...` - full-text product search through Elasticsearch
- `GET /api/products/{product_id}` - get one product
- `PATCH /api/products/{product_id}` - update product, admin only
- `DELETE /api/products/{product_id}` - remove product from public catalog, admin only

Cart, requires `Authorization: Bearer <token>`:

- `GET /api/cart/` - get current cart
- `POST /api/cart/add?product_id=...&quantity=1` - add product to cart
- `DELETE /api/cart/remove/{product_id}` - remove product from cart
- `DELETE /api/cart/clear` - clear cart

Orders, requires `Authorization: Bearer <token>`:

- `POST /api/orders/?delivery_address=...` - create order from cart
- `GET /api/orders/` - get current user's orders
- `GET /api/orders/admin` - get all orders with customer and item details, admin/manager only
- `PATCH /api/orders/{order_id}/status?status=...` - update order status, admin/manager only

Users:

- `GET /api/users/` - list users, admin only
- `PATCH /api/users/{user_id}/role` - assign `admin`, `manager`, or `customer` role, admin only

Realtime order updates:

- `WS /ws/orders/{order_id}` - subscribe to order status updates

System:

- `GET /health` - health check
- `GET /metrics` - Prometheus metrics

## Background Jobs

Celery Beat schedules two tasks:

- `daily_sales_report`: runs every day at 23:00 Asia/Tashkent time and logs delivered order count plus revenue for the day.
- `low_stock_alert`: runs every 30 minutes and logs active products with stock below 5 units.

## Search Synchronization

On API startup, products are synchronized to Elasticsearch through `app.services.es_sync.sync_all_products`. The search endpoint then reads from the configured `ES_INDEX` index.

## Authentication Notes

Protected endpoints expect a JWT bearer token. The helper in `app.core.security` creates HS256 tokens with `sub` set to the user id and expiration controlled by `ACCESS_TOKEN_EXPIRE_MINUTES`.

The seed script creates an admin user:

- Email: `admin@flowershop.uz`
- Password: `admin1234`

## Operational Notes

- Nginx proxies `/`, `/api/`, `/ws/`, `/metrics`, and `/openapi.json` to two API containers: `api_1` and `api_2`.
- Order creation is rate-limited with a Redis token bucket: capacity 5 requests, refill rate 0.5 tokens per second per client IP.
- API docs are served at `/api/docs` and `/api/redoc`.
- `docker compose logs -f api_1 api_2` is useful for API troubleshooting.
- `docker compose logs -f celery_worker celery_beat` is useful for scheduled task troubleshooting.

## Architecture

- **API:** FastAPI x 2 replicas behind Nginx
- **DB:** PostgreSQL 16 (primary data store)
- **Cache:** Redis 7 (cart, sessions, rate limiter)
- **Search:** Elasticsearch 8 (product full-text search)
- **Queue:** Celery + Redis (batch jobs)
- **Bot:** Telegram bot via aiogram (webhook mode)
- **Observability:** OpenTelemetry -> Prometheus + Grafana

## Team

| Name | Role |
|------|------|
| Amina Saidakhmedova  | DevOps / Infra |
| Amir Shayxutdinov | DevOps 2 / Auth |
| Aleksandrina Ryazanova | QA / Orders |
| Andrey Sedelkov | QA / Catalog |
| Xusan Samatov | Data / Pipeline |

## Changelog

### v1.0.0 - 2026-05-17

- Initial production release
- All R1-R13 requirements implemented
