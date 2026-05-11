"""Add order table for payments

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-11 13:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from open_webui.migrations.util import get_existing_tables

revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    existing = set(get_existing_tables())
    if 'order' not in existing:
        op.create_table(
            'order',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('user_id', sa.String(), nullable=False),
            sa.Column('plan_code', sa.String(length=32), nullable=False),
            sa.Column('period', sa.String(length=16), nullable=False, server_default='monthly'),
            sa.Column('amount_cents', sa.Integer(), nullable=False),
            sa.Column('status', sa.String(length=16), nullable=False, server_default='pending'),
            sa.Column('provider', sa.String(length=16), nullable=False, server_default='zpay'),
            sa.Column('provider_pay_type', sa.String(length=16), nullable=True),
            sa.Column('provider_trade_no', sa.String(length=64), nullable=True),
            sa.Column('paid_at', sa.BigInteger(), nullable=True),
            sa.Column('expires_at', sa.BigInteger(), nullable=False),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
            sa.Column('updated_at', sa.BigInteger(), nullable=False),
        )
        op.create_index('ix_order_user_id', 'order', ['user_id'])
        op.create_index('ix_order_status', 'order', ['status'])
        op.create_index('ix_order_provider_trade_no', 'order', ['provider_trade_no'])


def downgrade() -> None:
    existing = set(get_existing_tables())
    if 'order' in existing:
        for ix in ('ix_order_provider_trade_no', 'ix_order_status', 'ix_order_user_id'):
            try:
                op.drop_index(ix, table_name='order')
            except Exception:
                pass
        op.drop_table('order')
