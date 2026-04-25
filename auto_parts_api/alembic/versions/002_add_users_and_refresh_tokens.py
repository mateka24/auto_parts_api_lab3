"""Add users and refresh_tokens tables

Revision ID: 002
Revises: 001
Create Date: 2026-03-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Создаём таблицу пользователей
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('phone', sa.String(), nullable=True),
        sa.Column('password_hash', sa.String(), nullable=True),
        sa.Column('salt', sa.String(), nullable=True),
        sa.Column('yandex_id', sa.String(), nullable=True),
        sa.Column('vk_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_yandex_id'), 'users', ['yandex_id'], unique=True)
    op.create_index(op.f('ix_users_vk_id'), 'users', ['vk_id'], unique=True)
    
    # Создаём таблицу refresh токенов
    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token_hash', sa.String(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('is_revoked', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('user_agent', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index(op.f('ix_refresh_tokens_id'), 'refresh_tokens', ['id'], unique=False)
    op.create_index(op.f('ix_refresh_tokens_user_id'), 'refresh_tokens', ['user_id'], unique=False)
    
    # Добавляем owner_id в auto_parts
    op.add_column('auto_parts', sa.Column('owner_id', sa.Integer(), nullable=True))
    
    # Создаём foreign key constraint
    op.create_foreign_key(
        'fk_auto_parts_owner_id_users',
        'auto_parts', 'users',
        ['owner_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_index(op.f('ix_auto_parts_owner_id'), 'auto_parts', ['owner_id'], unique=False)


def downgrade() -> None:
    # Удаляем owner_id из auto_parts
    op.drop_index(op.f('ix_auto_parts_owner_id'), table_name='auto_parts')
    op.drop_constraint('fk_auto_parts_owner_id_users', 'auto_parts', type_='foreignkey')
    op.drop_column('auto_parts', 'owner_id')
    
    # Удаляем таблицу refresh_tokens
    op.drop_index(op.f('ix_refresh_tokens_user_id'), table_name='refresh_tokens')
    op.drop_index(op.f('ix_refresh_tokens_id'), table_name='refresh_tokens')
    op.drop_table('refresh_tokens')
    
    # Удаляем таблицу users
    op.drop_index(op.f('ix_users_vk_id'), table_name='users')
    op.drop_index(op.f('ix_users_yandex_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')
