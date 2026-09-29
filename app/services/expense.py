from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.branch import Branch
from app.database.models.expense import Expense, ExpenseCategory
from app.repositories.expense import ExpenseRepository
from app.schemas.expense import ExpenseCreate


def create_expense(
    db: Session,
    tenant_id: UUID,
    data: ExpenseCreate,
) -> Expense:
    """
    Create an expense for a tenant-owned branch.
    """

    branch = db.scalar(
        select(Branch).where(
            Branch.id == data.branch_id,
            Branch.tenant_id == tenant_id,
        )
    )

    if branch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found.",
        )

    expense = Expense(
        tenant_id=tenant_id,
        branch_id=data.branch_id,
        category=data.category,
        amount=data.amount,
        expense_date=data.expense_date,
        description=data.description,
    )

    repository = ExpenseRepository(db)

    return repository.create(expense)


def get_expenses(
    db: Session,
    tenant_id: UUID,
    branch_id: UUID | None = None,
    category: ExpenseCategory | None = None,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
) -> dict:
    """
    Return expenses for a tenant with optional filters.
    """

    if (
        start_at is not None
        and end_at is not None
        and start_at > end_at
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "start_at must be earlier than or equal to end_at."
            ),
        )

    if branch_id is not None:
        branch = db.scalar(
            select(Branch).where(
                Branch.id == branch_id,
                Branch.tenant_id == tenant_id,
            )
        )

        if branch is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Branch not found.",
            )

    repository = ExpenseRepository(db)

    expenses = repository.get_all(
        tenant_id=tenant_id,
        branch_id=branch_id,
        category=category,
        start_at=start_at,
        end_at=end_at,
    )

    return {
        "items": expenses,
        "total_count": len(expenses),
    }