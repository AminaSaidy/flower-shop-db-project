import asyncio
import uuid
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.core.config import settings

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def seed():
    engine = create_async_engine(settings.DATABASE_URL)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as db:
        await db.execute(text("""
            INSERT INTO users (id, email, password_hash, full_name, role)
            VALUES (:id, :email, :pw, :name, 'admin')
            ON CONFLICT (email) DO NOTHING
        """), {"id": str(uuid.uuid4()), "email": "admin@flowershop.uz",
               "pw": pwd.hash("admin1234"), "name": "Shop Admin"})

        categories = [
            ("roses",      "Roses",      "Classic roses"),
            ("bouquets",   "Bouquets",   "Mixed arrangements"),
            ("succulents", "Succulents", "Low-maintenance plants"),
            ("seasonal",   "Seasonal",   "What's blooming now"),
        ]
        cat_ids = {}
        for slug, name, desc in categories:
            cid = str(uuid.uuid4())
            cat_ids[slug] = cid
            await db.execute(text("""
                INSERT INTO categories (id, name, slug, description)
                VALUES (:id, :name, :slug, :desc)
                ON CONFLICT (slug) DO NOTHING
            """), {"id": cid, "name": name, "slug": slug, "desc": desc})

        await db.commit()

        rows = await db.execute(text("SELECT id, slug FROM categories"))
        cat_ids = {r.slug: str(r.id) for r in rows}

        products = [
            ("Red Rose Bouquet",    "red-rose-bouquet",    "roses",      50.0, 30, "romantic",    "red"),
            ("White Wedding Roses", "white-wedding-roses", "roses",      75.0, 20, "wedding",     "white"),
            ("Pink Birthday Mix",   "pink-birthday-mix",   "bouquets",   45.0, 25, "birthday",    "pink"),
            ("Spring Tulips",       "spring-tulips",       "seasonal",   35.0, 40, "any",         "yellow"),
            ("Succulent Trio",      "succulent-trio",      "succulents", 30.0, 50, "any",         "green"),
            ("Sunflower Joy",       "sunflower-joy",       "bouquets",   40.0, 35, "birthday",    "yellow"),
            ("Purple Lavender",     "purple-lavender",     "seasonal",   28.0, 45, "any",         "purple"),
            ("Anniversary Gold",    "anniversary-gold",    "roses",      90.0, 15, "anniversary", "orange"),
        ]
        for name, slug, cat, price, stock, occasion, color in products:
            await db.execute(text("""
                INSERT INTO products (id, category_id, name, slug, price, stock_quantity, occasion, color, is_active)
                VALUES (:id, :cat, :name, :slug, :price, :stock, :occasion, :color, true)
                ON CONFLICT (slug) DO NOTHING
            """), {"id": str(uuid.uuid4()), "cat": cat_ids[cat], "name": name,
                   "slug": slug, "price": price, "stock": stock,
                   "occasion": occasion, "color": color})

        await db.commit()
        print("✓ Seed complete")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed())