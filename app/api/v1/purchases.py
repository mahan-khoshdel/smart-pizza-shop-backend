from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_data
from app.core.dependencies import get_db
from app.schemas.purchase import (
    PurchaseCreate,
    PurchaseDetailResponse,
    PurchaseListResponse,
)
from app.schemas.purchase_receive import PurchaseReceiveRequest
from app.services.purchase import (
    create_purchase,
    get_purchase_detail,
    list_purchases,
    receive_purchase,
)


router = APIRouter(
    prefix="/purchases",
    tags=["Purchases"],
)


@router.post("")
def create_purchase_endpoint(
    purchase_data: PurchaseCreate,
    current_user: dict[str, UUID] = Depends(get_current_user_data),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Create a draft purchase."""

    purchase = create_purchase(
        db=db,
        tenant_id=current_user["tenant_id"],
        branch_id=purchase_data.branch_id,
        supplier_id=purchase_data.supplier_id,
        purchase_number=purchase_data.purchase_number,
        items=purchase_data.items,
        note=purchase_data.note,
    )

    return {
        "id": str(purchase.id),
        "purchase_number": purchase.purchase_number,
        "status": purchase.status,
    }


@router.get("", response_model=PurchaseListResponse)
def list_purchases_endpoint(
    branch_id: UUID | None = Query(default=None),
    supplier_id: UUID | None = Query(default=None),
    purchase_status: str | None = Query(default=None),
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    current_user: dict[str, UUID] = Depends(get_current_user_data),
    db: Session = Depends(get_db),
):
    """Return filtered purchases for the current tenant."""

    purchases, total_count = list_purchases(
        db=db,
        tenant_id=current_user["tenant_id"],
        branch_id=branch_id,
        supplier_id=supplier_id,
        purchase_status=purchase_status,
        start_date=start_date,
        end_date=end_date,
    )

    return {
        "items": [
            {
                "id": purchase.id,
                "tenant_id": purchase.tenant_id,
                "branch_id": purchase.branch_id,
                "supplier_id": purchase.supplier_id,
                "purchase_number": purchase.purchase_number,
                "purchase_date": purchase.purchase_date,
                "status": getattr(
                    purchase.status,
                    "value",
                    purchase.status,
                ),
                "note": purchase.note,
                "created_at": purchase.created_at,
                "updated_at": purchase.updated_at,
            }
            for purchase in purchases
        ],
        "total_count": total_count,
    }


@router.get(
    "/{purchase_id}",
    response_model=PurchaseDetailResponse,
)
def get_purchase_detail_endpoint(
    purchase_id: UUID,
    current_user: dict[str, UUID] = Depends(get_current_user_data),
    db: Session = Depends(get_db),
):
    """Return a purchase and all of its items."""

    return get_purchase_detail(
        db=db,
        purchase_id=purchase_id,
        tenant_id=current_user["tenant_id"],
    )


@router.post("/{purchase_id}/receive")
def receive_purchase_endpoint(
    purchase_id: UUID,
    receive_data: PurchaseReceiveRequest,
    current_user: dict[str, UUID] = Depends(get_current_user_data),
    db: Session = Depends(get_db),
):
    """Receive a draft purchase into inventory."""

    receive_purchase(
        db=db,
        purchase_id=purchase_id,
        tenant_id=current_user["tenant_id"],
        receive_items=receive_data.items,
    )

    return {
        "message": "Purchase received successfully.",
    }