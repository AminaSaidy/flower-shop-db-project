import json
from fastapi import APIRouter, Depends, HTTPException
from app.core.config import settings
from app.core.security import get_current_user
import redis.asyncio as aioredis

router = APIRouter(prefix="/cart", tags=["cart"])

CART_TTL = 7 * 24 * 3600


async def get_redis():
    return aioredis.from_url(settings.REDIS_URL)


def cart_key(user_id: str) -> str:
    return f"cart:{user_id}"


@router.get("/", summary="Get current cart")
async def get_cart(user: dict = Depends(get_current_user)):
    r = await get_redis()
    raw = await r.get(cart_key(user["user_id"]))
    items = json.loads(raw) if raw else []
    total = sum(i["price"] * i["quantity"] for i in items)
    return {"items": items, "total": total}


@router.post("/add", summary="Add product to cart")
async def add_to_cart(
    product_id: str,
    quantity: int = 1,
    user: dict = Depends(get_current_user)
):
    if quantity < 1:
        raise HTTPException(status_code=400, detail="Quantity must be >= 1")

    r = await get_redis()
    key = cart_key(user["user_id"])
    raw = await r.get(key)
    items: list = json.loads(raw) if raw else []

    for item in items:
        if item["product_id"] == product_id:
            item["quantity"] += quantity
            break
    else:
        items.append({"product_id": product_id, "quantity": quantity, "price": 0.0})

    await r.set(key, json.dumps(items), ex=CART_TTL)
    return {"message": "Added to cart", "items": items}


@router.delete("/remove/{product_id}", summary="Remove product from cart")
async def remove_from_cart(product_id: str, user: dict = Depends(get_current_user)):
    r = await get_redis()
    key = cart_key(user["user_id"])
    raw = await r.get(key)
    items = json.loads(raw) if raw else []
    items = [i for i in items if i["product_id"] != product_id]
    await r.set(key, json.dumps(items), ex=CART_TTL)
    return {"message": "Removed", "items": items}


@router.delete("/clear", summary="Clear entire cart")
async def clear_cart(user: dict = Depends(get_current_user)):
    r = await get_redis()
    await r.delete(cart_key(user["user_id"]))
    return {"message": "Cart cleared"}