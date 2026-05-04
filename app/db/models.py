import uuid
from sqlalchemy import (Column, String, Float, Integer, Boolean,
                         Text, DateTime, ForeignKey, CheckConstraint, UniqueConstraint)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email         = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name     = Column(String(255), nullable=False)
    phone         = Column(String(30))
    role          = Column(String(20), default="customer")
    created_at    = Column(DateTime(timezone=True), server_default=func.now())


class Category(Base):
    __tablename__ = "categories"
    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name        = Column(String(100), nullable=False)
    slug        = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text)
    products    = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"
    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id    = Column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"))
    name           = Column(String(255), nullable=False, index=True)
    slug           = Column(String(255), nullable=False, unique=True, index=True)
    description    = Column(Text)
    price          = Column(Float, nullable=False)
    stock_quantity = Column(Integer, default=0)
    occasion       = Column(String(50))
    color          = Column(String(50))
    image_url      = Column(String(500))
    is_active      = Column(Boolean, default=True, index=True)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())
    category       = relationship("Category", back_populates="products")


class Order(Base):
    __tablename__ = "orders"
    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id          = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True)
    status           = Column(String(30), default="pending", index=True)
    delivery_address = Column(Text, nullable=False)
    total_price      = Column(Float, nullable=False)
    created_at       = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at       = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    items            = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"
    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id   = Column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"))
    quantity   = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    order      = relationship("Order", back_populates="items")
    product    = relationship("Product")


class CartItem(Base):
    __tablename__ = "cart_items"
    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"))
    quantity   = Column(Integer, default=1)
    __table_args__ = (UniqueConstraint("user_id", "product_id"),)


class Review(Base):
    __tablename__ = "reviews"
    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), index=True)
    rating     = Column(Integer, nullable=False)
    comment    = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_reviews_rating"),
        UniqueConstraint("user_id", "product_id", name="uq_review_user_product"),
    )