"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-19
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("timezone", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("telegram_id", name="uq_users_telegram_id"),
    )
    op.create_table(
        "food_entries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("photo_file_id", sa.Text(), nullable=True),
        sa.Column("eaten_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("calories", sa.Numeric(10, 2), nullable=False),
        sa.Column("protein", sa.Numeric(10, 2), nullable=False),
        sa.Column("fat", sa.Numeric(10, 2), nullable=False),
        sa.Column("carbohydrates", sa.Numeric(10, 2), nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=True),
        sa.Column("message_id", sa.BigInteger(), nullable=True),
        sa.Column("recognition_error", sa.String(length=40), nullable=True),
        sa.CheckConstraint(
            "status IN ('draft', 'confirmed', 'cancelled', 'expired')",
            name="ck_food_entries_status",
        ),
    )
    op.create_index(
        "ix_food_entries_user_status_eaten",
        "food_entries",
        ["user_id", "status", "eaten_at"],
    )
    op.create_table(
        "food_entry_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "entry_id",
            sa.Uuid(),
            sa.ForeignKey("food_entries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("weight_g", sa.Numeric(7, 1), nullable=False),
        sa.Column("calories", sa.Numeric(10, 2), nullable=False),
        sa.Column("protein", sa.Numeric(10, 2), nullable=False),
        sa.Column("fat", sa.Numeric(10, 2), nullable=False),
        sa.Column("carbohydrates", sa.Numeric(10, 2), nullable=False),
        sa.Column("calories_per_100g", sa.Numeric(10, 2), nullable=False),
        sa.Column("protein_per_100g", sa.Numeric(10, 2), nullable=False),
        sa.Column("fat_per_100g", sa.Numeric(10, 2), nullable=False),
        sa.Column("carbohydrates_per_100g", sa.Numeric(10, 2), nullable=False),
        sa.Column("nutrition_source", sa.String(length=20), nullable=False),
        sa.Column("recognition_note", sa.Text(), nullable=True),
        sa.CheckConstraint("weight_g > 0", name="ck_food_entry_items_weight"),
    )
    op.create_index("ix_food_entry_items_entry_id", "food_entry_items", ["entry_id"])


def downgrade() -> None:
    op.drop_index("ix_food_entry_items_entry_id", table_name="food_entry_items")
    op.drop_table("food_entry_items")
    op.drop_index("ix_food_entries_user_status_eaten", table_name="food_entries")
    op.drop_table("food_entries")
    op.drop_table("users")
