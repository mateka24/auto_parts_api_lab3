"""Initial migration: create auto_parts table

Revision ID: 001
Revises: 
Create Date: 2026-03-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'auto_parts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('part_number', sa.String(), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_auto_parts_id'), 'auto_parts', ['id'], unique=False)
    op.create_index(op.f('ix_auto_parts_part_number'), 'auto_parts', ['part_number'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_auto_parts_part_number'), table_name='auto_parts')
    op.drop_index(op.f('ix_auto_parts_id'), table_name='auto_parts')
    op.drop_table('auto_parts')
