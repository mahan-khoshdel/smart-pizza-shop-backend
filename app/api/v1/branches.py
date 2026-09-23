from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_data
from app.database.connection import get_db
from app.schemas.branch import (
    BranchKitchenCapacityResponse,
    KitchenCapacityUpdate,
)
from app.services.branch import update_kitchen_capacity


router = APIRouter(
    prefix="/branches",
    tags=["Branches"],
)


@router.patch(
    "/{branch_id}/kitchen-capacity",
    response_model=BranchKitchenCapacityResponse,
)
def update_kitchen_capacity_endpoint(
    branch_id: UUID,
    data: KitchenCapacityUpdate,
    current_user_data: dict = Depends(get_current_user_data),
    db: Session = Depends(get_db),
):
    """
    Update the kitchen capacity of a branch.
    """

    branch = update_kitchen_capacity(
        db=db,
        tenant_id=current_user_data["tenant_id"],
        branch_id=branch_id,
        kitchen_capacity=data.kitchen_capacity,
    )

    return {
        "branch_id": branch.id,
        "name": branch.name,
        "kitchen_capacity": branch.kitchen_capacity,
    }