from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_data
from app.core.dependencies import get_db
from app.schemas.inventory import (
    ExpirySummaryResponse,
    InventoryConsumptionResponse,
    InventorySummaryResponse,
    InventoryValuationResponse,
    InventoryWasteAnalyticsResponse,
    InventoryWasteCreate,
    InventoryWasteResponse,
    LowStockResponse,
)
from app.schemas.inventory_consume import InventoryConsumeRequest
from app.services.inventory import (
    consume_inventory,
    get_expiry_summary,
    get_inventory_consumption_analytics,
    get_inventory_summary,
    get_inventory_valuation,
    get_inventory_waste_analytics,
    get_low_stock_items,
    record_inventory_waste,
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
    
    
@router.get(
    "/summary",
    response_model=InventorySummaryResponse,
)
def get_inventory_summary_endpoint(
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
    Return summarized inventory status for a branch.
    """

    return get_inventory_summary(
        db=db,
        tenant_id=current_user["tenant_id"],
        branch_id=branch_id,
        expiring_soon_days=expiring_soon_days,
    )
    
    
@router.get(
    "/valuation",
    response_model=InventoryValuationResponse,
)
def get_inventory_valuation_endpoint(
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
    Return monetary inventory valuation for a branch.
    """

    return get_inventory_valuation(
        db=db,
        tenant_id=current_user["tenant_id"],
        branch_id=branch_id,
        expiring_soon_days=expiring_soon_days,
    )
    
    
@router.get(
    "/consumption",
    response_model=InventoryConsumptionResponse,
)
def get_inventory_consumption_analytics_endpoint(
    branch_id: UUID,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    current_user: dict[str, UUID] = Depends(
        get_current_user_data,
    ),
    db: Session = Depends(get_db),
):
    """
    Return inventory consumption analytics for a branch.
    """

    return get_inventory_consumption_analytics(
        db=db,
        tenant_id=current_user["tenant_id"],
        branch_id=branch_id,
        start_at=start_at,
        end_at=end_at,
    )
    
    
@router.post(
    "/waste",
    response_model=InventoryWasteResponse,
    status_code=201,
)
def record_inventory_waste_endpoint(
    waste_data: InventoryWasteCreate,
    current_user: dict[str, UUID] = Depends(
        get_current_user_data,
    ),
    db: Session = Depends(get_db),
):
    """
    Record inventory waste using FEFO.
    """

    return record_inventory_waste(
        db=db,
        tenant_id=current_user["tenant_id"],
        branch_id=waste_data.branch_id,
        ingredient_id=waste_data.ingredient_id,
        quantity=waste_data.quantity,
        note=waste_data.note,
    )


@router.get(
    "/waste",
    response_model=InventoryWasteAnalyticsResponse,
)
def get_inventory_waste_analytics_endpoint(
    branch_id: UUID,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    current_user: dict[str, UUID] = Depends(
        get_current_user_data,
    ),
    db: Session = Depends(get_db),
):
    """
    Return inventory waste analytics for a branch.
    """

    return get_inventory_waste_analytics(
        db=db,
        tenant_id=current_user["tenant_id"],
        branch_id=branch_id,
        start_at=start_at,
        end_at=end_at,
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