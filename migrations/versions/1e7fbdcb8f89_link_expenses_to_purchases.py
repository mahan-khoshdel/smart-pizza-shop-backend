"""link expenses to purchases

Revision ID: 1e7fbdcb8f89
Revises: c24c10c5c847
Create Date: 2026-09-30 20:55:37.796237

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1e7fbdcb8f89"
down_revision: Union[str, Sequence[str], None] = "c24c10c5c847"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # ---------------------------------------------------------
    # 1. Add PURCHASE to the existing PostgreSQL enum
    # ---------------------------------------------------------
    op.execute(
        """
        ALTER TYPE expense_category
        ADD VALUE IF NOT EXISTS 'PURCHASE'
        """
    )

    # ---------------------------------------------------------
    # 2. Add purchase_id to expenses
    # ---------------------------------------------------------
    op.add_column(
        "expenses",
        sa.Column(
            "purchase_id",
            sa.Uuid(),
            nullable=True,
        ),
    )

    # ---------------------------------------------------------
    # 3. One purchase can create at most one expense
    # ---------------------------------------------------------
    op.create_index(
        "ix_expenses_purchase_id",
        "expenses",
        ["purchase_id"],
        unique=True,
    )

    # ---------------------------------------------------------
    # 4. Link expense to purchase
    # ---------------------------------------------------------
    op.create_foreign_key(
        "fk_expenses_purchase_id_purchases",
        "expenses",
        "purchases",
        ["purchase_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_constraint(
        "fk_expenses_purchase_id_purchases",
        "expenses",
        type_="foreignkey",
    )

    op.drop_index(
        "ix_expenses_purchase_id",
        table_name="expenses",
    )

    op.drop_column(
        "expenses",
        "purchase_id",
    )

    # PostgreSQL enum values cannot be safely removed with a simple
    # ALTER TYPE command. The PURCHASE enum value is therefore kept.