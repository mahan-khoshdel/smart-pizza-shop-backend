from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.database.models.expense import ExpenseCategory


class ExpenseCreate(BaseModel):
    """Represent a request to create an expense."""

    branch_id: UUID
    category: ExpenseCategory
    amount: Decimal = Field(gt=0)
    expense_date: datetime | None = None
    description: str | None = None


class ExpenseResponse(BaseModel):
    """Represent an expense."""

    id: UUID
    tenant_id: UUID
    branch_id: UUID
    category: ExpenseCategory
    amount: Decimal
    expense_date: datetime
    description: str | None
    created_at: datetime
    updated_at: datetime


class ExpenseListResponse(BaseModel):
    """Represent a list of expenses."""

    items: list[ExpenseResponse]
    total_count: int