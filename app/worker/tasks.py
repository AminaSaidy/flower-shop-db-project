import asyncio
import logging
from datetime import date

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.worker.celery_app import celery_app
from app.db.models import Order, Product
from app.core.config import settings

logger = logging.getLogger(__name__)


def get_session():
    engine = create_async_engine(settings.DATABASE_URL)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return Session, engine


@celery_app.task(name="app.worker.tasks.daily_sales_report")
def daily_sales_report():
    """Counts delivered orders and total revenue for today"""
    async def _run():
        Session, engine = get_session()
        async with Session() as db:
            result = await db.execute(
                select(
                    func.count(Order.id).label("order_count"),
                    func.coalesce(func.sum(Order.total_price), 0).label("total_revenue")
                )
                .where(func.date(Order.created_at) == date.today())
                .where(Order.status == "delivered")
            )
            row = result.one()
            logger.info(
                f"[Daily Report] {date.today()} — "
                f"Orders: {row.order_count}, Revenue: ${row.total_revenue:.2f}"
            )
        await engine.dispose()

    asyncio.run(_run())


@celery_app.task(name="app.worker.tasks.low_stock_alert")
def low_stock_alert():
    """Finds active products with stock < 5 units"""
    async def _run():
        Session, engine = get_session()
        async with Session() as db:
            result = await db.execute(
                select(Product.name, Product.stock_quantity)
                .where(Product.stock_quantity < 5)
                .where(Product.is_active == True)
                .order_by(Product.stock_quantity)
            )
            low_stock = result.all()
            if low_stock:
                for name, qty in low_stock:
                    logger.warning(f"[Low Stock] {name}: {qty} units left")
            else:
                logger.info("[Low Stock] All products sufficiently stocked")
        await engine.dispose()

    asyncio.run(_run())