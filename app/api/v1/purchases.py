from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_data
from app.core.dependencies import get_db
from app.schemas.purchase import PurchaseCreate
from app.schemas.purchase_receive import PurchaseReceiveRequest
from app.services.purchase import create_purchase, receive_purchase


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

@router.post("/{purchase_id}/receive")
def receive_purchase_endpoint(
    purchase_id: UUID,
    receive_data: PurchaseReceiveRequest,
    current_user: dict[str, UUID] = Depends(get_current_user_data),
    db: Session = Depends(get_db),
):
    receive_purchase(
        db=db,
        purchase_id=purchase_id,
        tenant_id=current_user["tenant_id"],
        receive_items=receive_data.items,
    )

    return {"message": "Purchase received successfully."}