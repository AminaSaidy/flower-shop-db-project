"""Allow one review per delivered order item

Revision ID: 003
Revises: 002
Create Date: 2026-05-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '003'
down_revision = '002'


def upgrade() -> None:
    op.add_column(
        'reviews',
        sa.Column(
            'order_id',
            UUID(as_uuid=True),
            sa.ForeignKey('orders.id', ondelete='SET NULL'),
            nullable=True,
        ),
    )
    op.create_index('ix_reviews_order_id', 'reviews', ['order_id'])
    op.drop_constraint('uq_review_user_product', 'reviews', type_='unique')
    op.create_unique_constraint(
        'uq_review_user_order_product',
        'reviews',
        ['user_id', 'order_id', 'product_id'],
    )


def downgrade() -> None:
    op.drop_constraint('uq_review_user_order_product', 'reviews', type_='unique')
    op.create_unique_constraint(
        'uq_review_user_product',
        'reviews',
        ['user_id', 'product_id'],
    )
    op.drop_index('ix_reviews_order_id', table_name='reviews')
    op.drop_column('reviews', 'order_id')
