"""Add phone column to user and verification_code table

Revision ID: cn0001
Revises: a0b1c2d3e4f5
Create Date: 2026-05-11 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from open_webui.migrations.util import get_existing_tables

revision: str = 'cn0001'
down_revision: Union[str, None] = 'a0b1c2d3e4f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    existing_tables = set(get_existing_tables())

    inspector = sa.inspect(op.get_bind())
    user_columns = {c['name'] for c in inspector.get_columns('user')} if 'user' in existing_tables else set()
    if 'phone' not in user_columns:
        with op.batch_alter_table('user') as batch:
            batch.add_column(sa.Column('phone', sa.String(length=32), nullable=True))
        op.create_index(
            'ix_user_phone',
            'user',
            ['phone'],
            unique=True,
            postgresql_where=sa.text('phone IS NOT NULL'),
            sqlite_where=sa.text('phone IS NOT NULL'),
        )

    if 'verification_code' not in existing_tables:
        op.create_table(
            'verification_code',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('target', sa.String(length=128), nullable=False),
            sa.Column('channel', sa.String(length=16), nullable=False),
            sa.Column('scene', sa.String(length=32), nullable=False),
            sa.Column('code_hash', sa.String(length=128), nullable=False),
            sa.Column('expires_at', sa.BigInteger(), nullable=False),
            sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('consumed_at', sa.BigInteger(), nullable=True),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
        )
        op.create_index(
            'ix_verification_code_target_scene',
            'verification_code',
            ['target', 'scene'],
        )
        op.create_index(
            'ix_verification_code_expires_at',
            'verification_code',
            ['expires_at'],
        )


def downgrade() -> None:
    existing_tables = set(get_existing_tables())

    if 'verification_code' in existing_tables:
        op.drop_index('ix_verification_code_expires_at', table_name='verification_code')
        op.drop_index('ix_verification_code_target_scene', table_name='verification_code')
        op.drop_table('verification_code')

    inspector = sa.inspect(op.get_bind())
    if 'user' in existing_tables:
        user_columns = {c['name'] for c in inspector.get_columns('user')}
        if 'phone' in user_columns:
            try:
                op.drop_index('ix_user_phone', table_name='user')
            except Exception:
                pass
            with op.batch_alter_table('user') as batch:
                batch.drop_column('phone')
