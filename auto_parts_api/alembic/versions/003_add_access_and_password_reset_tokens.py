"""Add access tokens and password reset tokens

Revision ID: 003
Revises: 002
Create Date: 2026-04-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("refresh_tokens", sa.Column("token_digest", sa.String(), nullable=True))
    op.create_index(op.f("ix_refresh_tokens_token_digest"), "refresh_tokens", ["token_digest"], unique=True)

    op.create_table(
        "access_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_digest", sa.String(), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("is_revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("user_agent", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_digest"),
    )
    op.create_index(op.f("ix_access_tokens_id"), "access_tokens", ["id"], unique=False)
    op.create_index(op.f("ix_access_tokens_user_id"), "access_tokens", ["user_id"], unique=False)
    op.create_index(op.f("ix_access_tokens_token_digest"), "access_tokens", ["token_digest"], unique=True)

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_digest", sa.String(), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("is_used", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_digest"),
    )
    op.create_index(op.f("ix_password_reset_tokens_id"), "password_reset_tokens", ["id"], unique=False)
    op.create_index(op.f("ix_password_reset_tokens_user_id"), "password_reset_tokens", ["user_id"], unique=False)
    op.create_index(op.f("ix_password_reset_tokens_token_digest"), "password_reset_tokens", ["token_digest"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_password_reset_tokens_token_digest"), table_name="password_reset_tokens")
    op.drop_index(op.f("ix_password_reset_tokens_user_id"), table_name="password_reset_tokens")
    op.drop_index(op.f("ix_password_reset_tokens_id"), table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")

    op.drop_index(op.f("ix_access_tokens_token_digest"), table_name="access_tokens")
    op.drop_index(op.f("ix_access_tokens_user_id"), table_name="access_tokens")
    op.drop_index(op.f("ix_access_tokens_id"), table_name="access_tokens")
    op.drop_table("access_tokens")

    op.drop_index(op.f("ix_refresh_tokens_token_digest"), table_name="refresh_tokens")
    op.drop_column("refresh_tokens", "token_digest")
