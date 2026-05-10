from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.db.session import get_db
from app.db.models import Order, OrderItem, Product, CartItem
from app.core.security import get_current_user

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/", summary="Create order from cart (rate limited R11)")
async def create_order(
    delivery_address: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    user_id = user["user_id"]

    result = await db.execute(
        select(CartItem).where(CartItem.user_id == user_id)
    )
    cart_items = result.scalars().all()

    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    total = 0.0
    order_items_data = []

    for item in cart_items:
        p_result = await db.execute(select(Product).where(Product.id == item.product_id))
        product = p_result.scalar_one_or_none()
        if not product or not product.is_active:
            raise HTTPException(status_code=400, detail=f"Product {item.product_id} unavailable")
        if product.stock_quantity < item.quantity:
            raise HTTPException(status_code=400, detail=f"Not enough stock for {product.name}")

        total += product.price * item.quantity
        order_items_data.append((product, item.quantity, product.price))

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

    for item in cart_items:
        await db.delete(item)

    await db.commit()

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
    return {"orders": [
        {"id": str(o.id), "status": o.status,
         "total": o.total_price, "created_at": str(o.created_at)}
        for o in orders
    ]}


@router.patch("/{order_id}/status", summary="Update order status (admin)")
async def update_order_status(
    order_id: str, status: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    valid_statuses = ["pending", "confirmed", "preparing", "delivering", "delivered", "cancelled"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Use: {valid_statuses}")

    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = status
    await db.commit()

    from app.api.endpoints.ws import notify_order_update
    await notify_order_update(order_id, status)

    return {"order_id": order_id, "new_status": status}