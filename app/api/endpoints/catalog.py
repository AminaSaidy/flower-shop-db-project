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

#нужно дописать эндпоинт поиска и айдипродукта

