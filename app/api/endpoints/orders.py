from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import json

from app.db.session import get_db
from app.db.models import Order, OrderItem, Product, User
from app.core.security import get_current_user
from app.api.endpoints.cart import cart_key, get_redis

router = APIRouter(prefix="/orders", tags=["orders"])

VALID_STATUSES = ["pending", "confirmed", "preparing", "delivering", "delivered", "cancelled"]


async def require_admin(db: AsyncSession, user: dict) -> User:
    result = await db.execute(select(User).where(User.id == user["user_id"]))
    current = result.scalar_one_or_none()
    if not current or current.role not in ("admin", "manager"):
        raise HTTPException(status_code=403, detail="Staff access required")
    return current


async def serialize_order(db: AsyncSession, order: Order, include_customer: bool = False) -> dict:
    items_result = await db.execute(
        select(OrderItem, Product)
        .join(Product, Product.id == OrderItem.product_id, isouter=True)
        .where(OrderItem.order_id == order.id)
    )
    items = [
        {
            "product_id": str(product.id) if product else str(item.product_id),
            "name": product.name if product else "Deleted product",
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "subtotal": item.quantity * item.unit_price,
        }
        for item, product in items_result.all()
    ]

    payload = {
        "id": str(order.id),
        "status": order.status,
        "total": order.total_price,
        "delivery_address": order.delivery_address,
        "created_at": str(order.created_at),
        "updated_at": str(order.updated_at),
        "items": items,
    }

    if include_customer:
        user_result = await db.execute(select(User).where(User.id == order.user_id))
        customer = user_result.scalar_one_or_none()
        payload["customer"] = {
            "id": str(customer.id) if customer else str(order.user_id),
            "email": customer.email if customer else None,
            "full_name": customer.full_name if customer else "Deleted user",
            "phone": customer.phone if customer else None,
        }

    return payload


@router.post("/", summary="Create order from cart (rate limited R11)")
async def create_order(
    delivery_address: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    user_id = user["user_id"]

    r = await get_redis()
    raw = await r.get(cart_key(user_id))
    cart_items = json.loads(raw) if raw else []

    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    total = 0.0
    order_items_data = []

    for item in cart_items:
        product_id = item["product_id"]
        quantity = item["quantity"]
        p_result = await db.execute(select(Product).where(Product.id == product_id))
        product = p_result.scalar_one_or_none()
        if not product or not product.is_active:
            raise HTTPException(status_code=400, detail=f"Product {product_id} unavailable")
        if product.stock_quantity < quantity:
            raise HTTPException(status_code=400, detail=f"Not enough stock for {product.name}")

        total += product.price * quantity
        order_items_data.append((product, quantity, product.price))

    order = Order(
        id=uuid.uuid4(), user_id=user_id,
        status="pending", delivery_address=delivery_address,
        total_price=total
    )
    db.add(order)
    await db.flush()

    for product, qty, price in order_items_data:
        db.add(OrderItem(
            id=uuid.uuid4(), order_id=order.id,
            product_id=product.id, quantity=qty, unit_price=price
        ))
        product.stock_quantity -= qty

    await db.commit()
    await r.delete(cart_key(user_id))

    from app.api.endpoints.ws import notify_order_update
    await notify_order_update(str(order.id), "pending")

    from app.core.telemetry import ORDER_COUNT
    ORDER_COUNT.inc()

    return {"order_id": str(order.id), "total": total, "status": "pending"}


@router.get("/", summary="Get user's orders")
async def get_orders(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    result = await db.execute(
        select(Order).where(Order.user_id == user["user_id"])
        .order_by(Order.created_at.desc())
    )
    orders = result.scalars().all()
    return {"orders": [await serialize_order(db, order) for order in orders]}


@router.get("/admin", summary="Get all orders (admin)")
async def get_all_orders(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    await require_admin(db, user)
    result = await db.execute(select(Order).order_by(Order.created_at.desc()))
    orders = result.scalars().all()
    return {"orders": [await serialize_order(db, order, include_customer=True) for order in orders]}


@router.patch("/{order_id}/status", summary="Update order status (admin)")
async def update_order_status(
    order_id: str, status: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    await require_admin(db, user)
    if status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Use: {VALID_STATUSES}")

    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = status
    await db.commit()

    from app.api.endpoints.ws import notify_order_update
    await notify_order_update(order_id, status)

    return {"order_id": order_id, "new_status": status}