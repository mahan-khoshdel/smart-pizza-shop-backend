from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_data
from app.core.dependencies import get_db
from app.database.models.expense import ExpenseCategory
from app.schemas.expense import (
    ExpenseCreate,
    ExpenseListResponse,
    ExpenseResponse,
)
from app.services.expense import (
    create_expense,
    get_expenses,
)


router = APIRouter(
    prefix="/expenses",
    tags=["Expenses"],
)


@router.post(
    "",
    response_model=ExpenseResponse,
    status_code=201,
)
def create_expense_endpoint(
    expense_data: ExpenseCreate,
    current_user: dict[str, UUID] = Depends(
        get_current_user_data,
    ),
    db: Session = Depends(get_db),
):
    """
    Create a new expense.
    """

    return create_expense(
        db=db,
        tenant_id=current_user["tenant_id"],
        data=expense_data,
    )


@router.get(
    "",
    response_model=ExpenseListResponse,
)
def get_expenses_endpoint(
    branch_id: UUID | None = None,
    category: ExpenseCategory | None = None,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    current_user: dict[str, UUID] = Depends(
        get_current_user_data,
    ),
    db: Session = Depends(get_db),
):
    """
    Return expenses with optional filters.
    """

    return get_expenses(
        db=db,
        tenant_id=current_user["tenant_id"],
        branch_id=branch_id,
        category=category,
        start_at=start_at,
        end_at=end_at,
    )