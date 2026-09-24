from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_data
from app.database.connection import get_db
from app.database.models.order import OrderStatus
from app.schemas.kitchen import KitchenQueueResponse
from app.schemas.order import (
    KitchenWorkloadResponse,
    OrderCreate,
    OrderIngredientRequirementsResponse,
    OrderResponse,
    OrderStatusHistoryResponse,
    OrderStatusUpdate,
)
from app.services.order import (
    cancel_order,
    consume_order_inventory,
    create_order,
    get_kitchen_orders,
    get_kitchen_queue,
    get_kitchen_workload,
    get_order,
    get_orders,
    get_order_ingredient_requirements,
    get_order_status_history,
    update_order_status,
)


router = APIRouter(
    prefix="/orders",
    tags=["Orders"],
)


@router.post(
    "",
    response_model=OrderResponse,
    status_code=201,
)
def create_order_endpoint(
    order_data: OrderCreate,
    current_user=Depends(get_current_user_data),
    db: Session = Depends(get_db),
):
    """
    Create a new order for the current tenant.
    """

    return create_order(
        db=db,
        tenant_id=current_user["tenant_id"],
        data=order_data,
    )


@router.get("", response_model=list[OrderResponse])
def get_orders_endpoint(
    status: OrderStatus | None = None,
    current_user_data: dict = Depends(get_current_user_data),
    db: Session = Depends(get_db),
):
    """
    Return orders for the current tenant.

    An optional status filter can be used to return only orders
    with a specific status.
    """
    return get_orders(
        db=db,
        tenant_id=current_user_data["tenant_id"],
        status=status,
    )


@router.get(
    "/{order_id}/ingredient-requirements",
    response_model=OrderIngredientRequirementsResponse,
)
def get_order_ingredient_requirements_endpoint(
    order_id: UUID,
    current_user=Depends(get_current_user_data),
    db: Session = Depends(get_db),
):
    """
    Calculate ingredient requirements for an order from its recipes.
    """

    return get_order_ingredient_requirements(
        db=db,
        tenant_id=current_user["tenant_id"],
        order_id=order_id,
    )

    
@router.get(
    "/{order_id}/status-history",
    response_model=list[OrderStatusHistoryResponse],
)
def get_order_status_history_endpoint(
    order_id: UUID,
    current_user_data: dict = Depends(get_current_user_data),
    db: Session = Depends(get_db),
):
    """
    Return the complete status history of an order.
    """
    return get_order_status_history(
        db=db,
        order_id=order_id,
        tenant_id=current_user_data["tenant_id"],
    )


@router.patch(
    "/{order_id}/status",
    response_model=OrderResponse,
)
def update_order_status_endpoint(
    order_id: UUID,
    status_data: OrderStatusUpdate,
    current_user=Depends(get_current_user_data),
    db: Session = Depends(get_db),
):
    """
    Update an order status according to the allowed order workflow.
    """

    return update_order_status(
        db=db,
        tenant_id=current_user["tenant_id"],
        order_id=order_id,
        new_status=status_data.status,
    )


@router.post(
    "/{order_id}/cancel",
    response_model=OrderResponse,
)
def cancel_order_endpoint(
    order_id: UUID,
    current_user=Depends(get_current_user_data),
    db: Session = Depends(get_db),
):
    """
    Cancel an order when its current status allows cancellation.
    """

    return cancel_order(
        db=db,
        tenant_id=current_user["tenant_id"],
        order_id=order_id,
    )

    
@router.post(
    "/{order_id}/consume-inventory",
    response_model=OrderResponse,
)
def consume_order_inventory_endpoint(
    order_id: UUID,
    current_user=Depends(get_current_user_data),
    db: Session = Depends(get_db),
):
    """
    Consume inventory required by a completed order using FEFO.
    """

    return consume_order_inventory(
        db=db,
        tenant_id=current_user["tenant_id"],
        order_id=order_id,
    )

    
@router.get(
    "/kitchen",
    response_model=list[OrderResponse],
)
def get_kitchen_orders_endpoint(
    branch_id: UUID,
    current_user_data: dict = Depends(get_current_user_data),
    db: Session = Depends(get_db),
):
    """
    Return PREPARING and READY orders for a specific branch.
    """
    return get_kitchen_orders(
        db=db,
        tenant_id=current_user_data["tenant_id"],
        branch_id=branch_id,
    )

    
@router.get(
    "/kitchen/workload",
    response_model=KitchenWorkloadResponse,
)
def get_kitchen_workload_endpoint(
    branch_id: UUID,
    current_user_data: dict = Depends(get_current_user_data),
    db: Session = Depends(get_db),
):
    """
    Return the current kitchen workload for a specific branch.
    """
    return get_kitchen_workload(
        db=db,
        tenant_id=current_user_data["tenant_id"],
        branch_id=branch_id,
    )


@router.get(
    "/kitchen/queue",
    response_model=KitchenQueueResponse,
)
def get_kitchen_queue_endpoint(
    branch_id: UUID,
    current_user_data: dict = Depends(get_current_user_data),
    db: Session = Depends(get_db),
):
    """
    Return the current preparing-order queue for a branch.
    """
    return get_kitchen_queue(
        db=db,
        tenant_id=current_user_data["tenant_id"],
        branch_id=branch_id,
    )


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
)
def get_order_endpoint(
    order_id: UUID,
    current_user=Depends(get_current_user_data),
    db: Session = Depends(get_db),
):
    """
    Return a single order for the current tenant.
    """

    return get_order(
        db=db,
        tenant_id=current_user["tenant_id"],
        order_id=order_id,
    )