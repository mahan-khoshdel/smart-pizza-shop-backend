from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_data
from app.core.dependencies import get_db
from app.schemas.inventory_consume import InventoryConsumeRequest
from app.services.inventory import consume_inventory


router = APIRouter(
    prefix="/inventory",
    tags=["Inventory"],
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