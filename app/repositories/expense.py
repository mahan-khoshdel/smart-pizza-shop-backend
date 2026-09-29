from datetime import datetime
from uuid import UUID

from sqlalchemy import select

from sqlalchemy.orm import Session

from app.database.models.expense import Expense, ExpenseCategory


class ExpenseRepository:
    """Handle database operations related to expenses."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        expense: Expense,
    ) -> Expense:
        """Create and persist an expense."""

        self.db.add(expense)
        self.db.commit()
        self.db.refresh(expense)

        return expense

    def get_all(
        self,
        tenant_id: UUID,
        branch_id: UUID | None = None,
        category: ExpenseCategory | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> list[Expense]:
        """Return expenses for a tenant with optional filters."""

        statement = select(Expense).where(
            Expense.tenant_id == tenant_id,
        )

        if branch_id is not None:
            statement = statement.where(
                Expense.branch_id == branch_id,
            )

        if category is not None:
            statement = statement.where(
                Expense.category == category,
            )

        if start_at is not None:
            statement = statement.where(
                Expense.expense_date >= start_at,
            )

        if end_at is not None:
            statement = statement.where(
                Expense.expense_date <= end_at,
            )

        statement = statement.order_by(
            Expense.expense_date.desc(),
            Expense.created_at.desc(),
        )

        return list(
            self.db.scalars(statement).all()
        )