from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_data
from app.database.connection import get_db
from app.database.models.order import OrderStatus
from app.schemas.order import (
    OrderCreate,
    OrderResponse,
    OrderStatusUpdate,
)
from app.services.order import (
    cancel_order,
    create_order,
    get_order,
    get_orders,
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

    
@router.get(
    "",
    response_model=list[OrderResponse],
)
def get_orders_endpoint(
    current_user=Depends(get_current_user_data),
    db: Session = Depends(get_db),
):
    """
    Return all orders for the current tenant.
    """

    return get_orders(
        db=db,
        tenant_id=current_user["tenant_id"],
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