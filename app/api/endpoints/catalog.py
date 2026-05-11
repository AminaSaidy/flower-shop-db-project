import re
import uuid
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from app.db.session import get_db
from app.db.models import Category, Order, OrderItem, Product, Review, User
from app.core.security import get_current_user
from app.core.config import settings
import redis.asyncio as aioredis

router = APIRouter(prefix="/products", tags=["catalog"])


class ProductCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    price: float = Field(gt=0)
    stock: int = Field(default=0, ge=0)
    category: str | None = Field(default=None, max_length=100)
    description: str | None = None
    occasion: str | None = Field(default=None, max_length=50)
    color: str | None = Field(default=None, max_length=50)
    image_url: str | None = Field(default=None, max_length=500)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    price: float | None = Field(default=None, gt=0)
    stock: int | None = Field(default=None, ge=0)
    category: str | None = Field(default=None, max_length=100)
    description: str | None = None
    occasion: str | None = Field(default=None, max_length=50)
    color: str | None = Field(default=None, max_length=50)
    image_url: str | None = Field(default=None, max_length=500)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or f"product-{uuid.uuid4().hex[:8]}"


async def require_admin(db: AsyncSession, user: dict) -> User:
    result = await db.execute(select(User).where(User.id == user["user_id"]))
    current = result.scalar_one_or_none()
    if not current or current.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current


def product_payload(product: Product) -> dict:
    return {
        "id": str(product.id),
        "name": product.name,
        "price": product.price,
        "description": product.description,
        "color": product.color,
        "occasion": product.occasion,
        "stock": product.stock_quantity,
        "image_url": product.image_url,
    }

@router.get("/", summary="List products with optional filters")
async def get_products(
    category: str  = Query(None, description="Filter by category slug"),
    occasion: str  = Query(None, description="birthday, wedding, anniversary, any"),
    color:    str  = Query(None, description="red, white, pink, yellow..."),
    db: AsyncSession = Depends(get_db)
):
    r = aioredis.from_url(settings.REDIS_URL)
    cache_key = f"products:{category}:{occasion}:{color}"

    cached = await r.get(cache_key)
    if cached:
        return json.loads(cached)

    q = select(Product).where(Product.is_active == True)

    if occasion:
        q = q.where(Product.occasion == occasion)
    if color:
        q = q.where(Product.color == color)
    if category:
        q = q.join(Category).where(Category.slug == category)

    result = await db.execute(q)
    products = result.scalars().all()

    response = {"products": [product_payload(p) for p in products]}
    await r.set(cache_key, json.dumps(response), ex=60)
    return response


@router.post("/", summary="Create product (admin)")
async def create_product(
    payload: ProductCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    await require_admin(db, user)

    category_id = None
    if payload.category:
        cat_result = await db.execute(select(Category).where(Category.slug == payload.category))
        category = cat_result.scalar_one_or_none()
        if not category:
            raise HTTPException(status_code=400, detail="Unknown category")
        category_id = category.id

    base_slug = slugify(payload.name)
    slug = base_slug
    existing = await db.execute(select(Product).where(Product.slug == slug))
    if existing.scalar_one_or_none():
        slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"

    product = Product(
        id=uuid.uuid4(),
        category_id=category_id,
        name=payload.name,
        slug=slug,
        description=payload.description,
        price=payload.price,
        stock_quantity=payload.stock,
        occasion=payload.occasion,
        color=payload.color,
        image_url=payload.image_url,
        is_active=True,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)

    from app.services.es_sync import index_product
    await index_product(product)

    return product_payload(product)

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

    return product_payload(product)


@router.post("/{product_id}/reviews", summary="Add product review")
async def add_review(
    product_id: str,
    rating: int,
    comment: str | None = None,
    order_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    if not 1 <= rating <= 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    product_result = await db.execute(
        select(Product.id).where(Product.id == product_id, Product.is_active == True)
    )
    if not product_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Product not found")

    delivered_query = (
        select(Order.id)
        .select_from(OrderItem)
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            Order.user_id == user["user_id"],
            Order.status == "delivered",
            OrderItem.product_id == product_id,
        )
        .limit(1)
    )
    if order_id:
        delivered_query = delivered_query.where(Order.id == order_id)

    delivered_result = await db.execute(delivered_query)
    delivered_order_id = delivered_result.scalar_one_or_none()
    if not delivered_order_id:
        raise HTTPException(status_code=403, detail="Only delivered products can be reviewed")

    review = Review(
        id=uuid.uuid4(),
        user_id=user["user_id"],
        order_id=delivered_order_id,
        product_id=product_id,
        rating=rating,
        comment=comment,
    )
    db.add(review)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Review already exists for this order")

    return {"message": "Review added", "rating": rating, "order_id": str(delivered_order_id)}


@router.get("/{product_id}/reviews", summary="Get product reviews")
async def get_reviews(product_id: str, db: AsyncSession = Depends(get_db)):
    product_result = await db.execute(
        select(Product.id).where(Product.id == product_id, Product.is_active == True)
    )
    if not product_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Product not found")

    result = await db.execute(
        select(Review).where(Review.product_id == product_id).order_by(Review.created_at.desc())
    )
    reviews = result.scalars().all()
    average_rating = (
        round(sum(review.rating for review in reviews) / len(reviews), 1)
        if reviews else None
    )
    sold_result = await db.execute(
        select(func.coalesce(func.sum(OrderItem.quantity), 0))
        .join(Order, Order.id == OrderItem.order_id)
        .where(OrderItem.product_id == product_id, Order.status == "delivered")
    )
    sold_count = int(sold_result.scalar_one() or 0)
    return {
        "average_rating": average_rating,
        "review_count": len(reviews),
        "sold_count": sold_count,
        "reviews": [
            {
                "rating": review.rating,
                "comment": review.comment,
                "created_at": str(review.created_at),
                "order_id": str(review.order_id) if review.order_id else None,
            }
            for review in reviews
        ]
    }


@router.patch("/{product_id}", summary="Update product (admin)")
async def update_product(
    product_id: str,
    payload: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    await require_admin(db, user)
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    data = payload.model_dump(exclude_unset=True)
    if "category" in data:
        category_slug = data.pop("category")
        if category_slug:
            cat_result = await db.execute(select(Category).where(Category.slug == category_slug))
            category = cat_result.scalar_one_or_none()
            if not category:
                raise HTTPException(status_code=400, detail="Unknown category")
            product.category_id = category.id
        elif category_slug is None:
            product.category_id = None

    if "stock" in data:
        product.stock_quantity = data.pop("stock")

    for field, value in data.items():
        setattr(product, field, value)

    await db.commit()
    await db.refresh(product)

    from app.services.es_sync import index_product
    await index_product(product)

    return product_payload(product)


@router.delete("/{product_id}", summary="Deactivate product (admin)")
async def delete_product(
    product_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    await require_admin(db, user)
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product.is_active = False
    await db.commit()
    await db.refresh(product)

    from app.services.es_sync import index_product
    await index_product(product)

    return {"message": "Product deleted", "product_id": product_id}
