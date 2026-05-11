from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.endpoints import catalog, orders, cart, ws
from app.bot.main import router_bot
from app.core.rate_limiter import rate_limit_middleware
from app.core.telemetry import setup_telemetry

app = FastAPI(
    title="Flower Shop API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

#для фронта
app.add_middleware(CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

#R11
app.add_middleware(BaseHTTPMiddleware, dispatch=rate_limit_middleware)

app.include_router(catalog.router, prefix="/api")
app.include_router(orders.router,  prefix="/api")
app.include_router(cart.router,    prefix="/api")
app.include_router(ws.router)
app.include_router(router_bot)      

#R12
setup_telemetry(app)

@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok"}

#При старте API синхронизируем все продукты в Elasticsearch
@app.on_event("startup")
async def startup_event():
    from app.services.es_sync import sync_all_products
    from app.db.session import async_session
    async with async_session() as db:
        await sync_all_products(db)