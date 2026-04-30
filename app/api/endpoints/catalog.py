from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.db.models import Product, Category

router = APIRouter(prefix="/products", tags=["catalog"])

@router.get("/", summary="List products with optional filters")
async def get_products(
    category: str  = Query(None, description="Filter by category slug"),
    occasion: str  = Query(None, description="birthday, wedding, anniversary, any"),
    color:    str  = Query(None, description="red, white, pink, yellow..."),
    db: AsyncSession = Depends(get_db)
):
    q = select(Product).where(Product.is_active == True)

    if occasion:
        q = q.where(Product.occasion == occasion)
    if color:
        q = q.where(Product.color == color)
    if category:
        q = q.join(Category).where(Category.slug == category)

    result = await db.execute(q)
    products = result.scalars().all()

    return {"products": [
        {"id": str(p.id), "name": p.name, "price": p.price,
         "color": p.color, "occasion": p.occasion,
         "stock": p.stock_quantity, "image_url": p.image_url}
        for p in products
    ]}

@router.get("/search", summary="Full-text search via Elasticsearch (R5)")
async def search_products(q: str = Query(..., description="Search query")):
    """Поиск через Elasticsearch — быстрее и умнее чем SQL LIKE (R5)."""
    from app.services.es_sync import search_products_es
    results = await search_products_es(q)
    return {"results": results}

@router.get("/{product_id}", summary="Get single product")
async def get_product(product_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Product).where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return {"id": str(product.id), "name": product.name,
            "price": product.price, "description": product.description,
            "color": product.color, "occasion": product.occasion,
            "stock": product.stock_quantity, "image_url": product.image_url}
#finish