from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_data
from app.core.dependencies import get_db
from app.schemas.inventory import (
    ExpirySummaryResponse,
    LowStockResponse,
)
from app.schemas.inventory_consume import InventoryConsumeRequest
from app.services.inventory import (
    consume_inventory,
    get_expiry_summary,
    get_low_stock_items,
)

router = APIRouter(
    prefix="/inventory",
    tags=["Inventory"],
)


@router.get(
    "/low-stock",
    response_model=list[LowStockResponse],
)
def get_low_stock_items_endpoint(
    branch_id: UUID,
    current_user: dict[str, UUID] = Depends(
        get_current_user_data,
    ),
    db: Session = Depends(get_db),
):
    """
    Return active inventory items at or below reorder level.
    """

    return get_low_stock_items(
        db=db,
        tenant_id=current_user["tenant_id"],
        branch_id=branch_id,
    )


@router.get(
    "/expiry",
    response_model=ExpirySummaryResponse,
)
def get_expiry_summary_endpoint(
    branch_id: UUID,
    expiring_soon_days: int = Query(
        default=7,
        ge=0,
        le=365,
    ),
    current_user: dict[str, UUID] = Depends(
        get_current_user_data,
    ),
    db: Session = Depends(get_db),
):
    """
    Return expired and soon-to-expire inventory batches.
    """

    return get_expiry_summary(
        db=db,
        tenant_id=current_user["tenant_id"],
        branch_id=branch_id,
        expiring_soon_days=expiring_soon_days,
    )


@router.post("/consume")
def consume_inventory_endpoint(
    consume_data: InventoryConsumeRequest,
    current_user: dict[str, UUID] = Depends(get_current_user_data),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Consume ingredient inventory using FEFO."""

    consume_inventory(
        db=db,
        tenant_id=current_user["tenant_id"],
        branch_id=consume_data.branch_id,
        ingredient_id=consume_data.ingredient_id,
        quantity=consume_data.quantity,
    )

    return {
        "message": "Inventory consumed successfully.",
    }