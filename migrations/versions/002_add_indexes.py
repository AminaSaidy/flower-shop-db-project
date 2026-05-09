"""Performance indexes

Revision ID: 002
Revises: 001
Create Date: 2026-05-09
"""
from alembic import op

revision = '002'
down_revision = '001'


def upgrade() -> None:
    op.create_index('ix_orders_user_status', 'orders', ['user_id', 'status'])
    op.create_index('ix_products_occasion', 'products', ['occasion'])
    op.create_index('ix_products_color', 'products', ['color'])
    op.create_index('ix_products_category_active', 'products', ['category_id', 'is_active'])


def downgrade() -> None:
    op.drop_index('ix_orders_user_status')
    op.drop_index('ix_products_occasion')
    op.drop_index('ix_products_color')
    op.drop_index('ix_products_category_active')