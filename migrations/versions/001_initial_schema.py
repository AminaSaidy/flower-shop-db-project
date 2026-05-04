from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(30)),
        sa.Column('role', sa.String(20), server_default='customer'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    op.create_table('categories',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False),
        sa.Column('description', sa.Text),
    )
    op.create_index('ix_categories_slug', 'categories', ['slug'], unique=True)

    op.create_table('products',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('category_id', UUID(as_uuid=True),
                  sa.ForeignKey('categories.id', ondelete='SET NULL')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('price', sa.Float, nullable=False),
        sa.Column('stock_quantity', sa.Integer, server_default='0'),
        sa.Column('occasion', sa.String(50)),
        sa.Column('color', sa.String(50)),
        sa.Column('image_url', sa.String(500)),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_products_slug', 'products', ['slug'], unique=True)
    op.create_index('ix_products_category_id', 'products', ['category_id'])
    op.create_index('ix_products_is_active', 'products', ['is_active'])

    op.create_table('orders',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('status', sa.String(30), server_default='pending'),
        sa.Column('delivery_address', sa.Text, nullable=False),
        sa.Column('total_price', sa.Float, nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_orders_user_id', 'orders', ['user_id'])
    op.create_index('ix_orders_status', 'orders', ['status'])
    op.create_index('ix_orders_created_at', 'orders', ['created_at'])

    op.create_table('order_items',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('order_id', UUID(as_uuid=True),
                  sa.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('product_id', UUID(as_uuid=True),
                  sa.ForeignKey('products.id', ondelete='SET NULL')),
        sa.Column('quantity', sa.Integer, nullable=False),
        sa.Column('unit_price', sa.Float, nullable=False),
    )
    op.create_index('ix_order_items_order_id', 'order_items', ['order_id'])

    op.create_table('cart_items',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('product_id', UUID(as_uuid=True),
                  sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False),
        sa.Column('quantity', sa.Integer, server_default='1'),
        sa.UniqueConstraint('user_id', 'product_id', name='uq_cart_user_product'),
    )

    op.create_table('reviews',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('product_id', UUID(as_uuid=True),
                  sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False),
        sa.Column('rating', sa.Integer, nullable=False),
        sa.Column('comment', sa.Text),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint('rating >= 1 AND rating <= 5', name='ck_reviews_rating'),
        sa.UniqueConstraint('user_id', 'product_id', name='uq_review_user_product'),
    )
    op.create_index('ix_reviews_product_id', 'reviews', ['product_id'])


def downgrade() -> None:
    op.drop_table('reviews')
    op.drop_table('cart_items')
    op.drop_table('order_items')
    op.drop_table('orders')
    op.drop_table('products')
    op.drop_table('categories')
    op.drop_table('users')