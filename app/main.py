from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
import os

from app.api.endpoints import auth, catalog, orders, cart, users, ws
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
app.include_router(auth.router,    prefix="/api")
app.include_router(users.router,   prefix="/api")
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


@app.exception_handler(404)
async def custom_404_handler(request: Request, exc: StarletteHTTPException):
    if not request.url.path.startswith("/api/"):
        return RedirectResponse("/404.html")
    return JSONResponse(status_code=404, content={"detail": "Not Found"})

app.mount("/", StaticFiles(directory="app/static", html=True), name="frontend")
