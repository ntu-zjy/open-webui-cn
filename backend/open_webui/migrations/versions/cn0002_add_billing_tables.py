"""Add billing tables: plan, subscription, usage_log

Revision ID: cn0002
Revises: cn0001
Create Date: 2026-05-11 12:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from open_webui.migrations.util import get_existing_tables

revision: str = 'cn0002'
down_revision: Union[str, None] = 'cn0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    existing = set(get_existing_tables())

    if 'plan' not in existing:
        op.create_table(
            'plan',
            sa.Column('code', sa.String(length=32), primary_key=True),
            sa.Column('name', sa.String(length=64), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('monthly_price_cents', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('yearly_price_cents', sa.Integer(), nullable=True),
            sa.Column('monthly_msg_limit', sa.Integer(), nullable=False, server_default='-1'),
            sa.Column('monthly_token_limit', sa.BigInteger(), nullable=False, server_default='-1'),
            sa.Column('allowed_model_pattern', sa.Text(), nullable=True),
            sa.Column('features_json', sa.JSON(), nullable=True),
            sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
            sa.Column('updated_at', sa.BigInteger(), nullable=False),
        )

    if 'subscription' not in existing:
        op.create_table(
            'subscription',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('user_id', sa.String(), nullable=False),
            sa.Column('plan_code', sa.String(length=32), nullable=False),
            sa.Column('status', sa.String(length=16), nullable=False, server_default='active'),
            sa.Column('started_at', sa.BigInteger(), nullable=False),
            sa.Column('expires_at', sa.BigInteger(), nullable=False),
            sa.Column('auto_renew', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('source_order_id', sa.String(), nullable=True),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
            sa.Column('updated_at', sa.BigInteger(), nullable=False),
        )
        op.create_index('ix_subscription_user_id', 'subscription', ['user_id'])
        op.create_index('ix_subscription_expires_at', 'subscription', ['expires_at'])

    if 'usage_log' not in existing:
        op.create_table(
            'usage_log',
            sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column('user_id', sa.String(), nullable=False),
            sa.Column('model', sa.String(length=128), nullable=False),
            sa.Column('prompt_tokens', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('completion_tokens', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('cost_cents', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('request_id', sa.String(length=64), nullable=True),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
        )
        op.create_index('ix_usage_log_user_created', 'usage_log', ['user_id', 'created_at'])
        op.create_index('ix_usage_log_model', 'usage_log', ['model'])


def downgrade() -> None:
    existing = set(get_existing_tables())
    if 'usage_log' in existing:
        try:
            op.drop_index('ix_usage_log_model', table_name='usage_log')
        except Exception:
            pass
        try:
            op.drop_index('ix_usage_log_user_created', table_name='usage_log')
        except Exception:
            pass
        op.drop_table('usage_log')
    if 'subscription' in existing:
        try:
            op.drop_index('ix_subscription_expires_at', table_name='subscription')
        except Exception:
            pass
        try:
            op.drop_index('ix_subscription_user_id', table_name='subscription')
        except Exception:
            pass
        op.drop_table('subscription')
    if 'plan' in existing:
        op.drop_table('plan')
