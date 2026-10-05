from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.database.models.order import OrderStatus
from app.schemas.order import OrderCreate
from app.services.order import (
    cancel_order,
    create_order,
    get_order_status_history,
    update_order_status,
)

TENANT_ID = UUID("25291ef5-0240-4042-aabc-b92c5aa4957a")
BRANCH_ID = UUID("6146f071-baf4-40e9-bbff-71f86e0a7770")
PRODUCT_VARIANT_ID = UUID(
    "7c065b06-1422-446b-a163-d6a30b4b659b"
)


def _create_test_order(db: Session):
    """
    Create a unique order for cancellation tests.
    """

    order_number = f"TEST-CANCEL-{uuid4().hex[:8]}"

    order_data = OrderCreate(
        branch_id=BRANCH_ID,
        customer_id=None,
        customer_address_id=None,
        order_number=order_number,
        order_type="DINE_IN",
        note="Automated cancellation test order.",
        items=[
            {
                "product_variant_id": PRODUCT_VARIANT_ID,
                "quantity": 1,
            }
        ],
    )

    return create_order(
        db=db,
        tenant_id=TENANT_ID,
        data=order_data,
    )


@pytest.mark.parametrize(
    "preparation_status",
    [
        OrderStatus.REGISTERED,
        OrderStatus.PREPARING,
        OrderStatus.READY,
    ],
)
def test_order_can_be_cancelled_from_allowed_statuses(
    db_session: Session,
    preparation_status: OrderStatus,
):
    """
    Verify that orders can be cancelled from every
    status that allows cancellation.
    """

    created_order = _create_test_order(db_session)
    order_id = created_order["id"]

    assert created_order["status"] == OrderStatus.REGISTERED

    if preparation_status == OrderStatus.PREPARING:
        preparing_order = update_order_status(
            db=db_session,
            tenant_id=TENANT_ID,
            order_id=order_id,
            new_status=OrderStatus.PREPARING,
        )

        assert preparing_order["status"] == OrderStatus.PREPARING

    elif preparation_status == OrderStatus.READY:
        preparing_order = update_order_status(
            db=db_session,
            tenant_id=TENANT_ID,
            order_id=order_id,
            new_status=OrderStatus.PREPARING,
        )

        assert preparing_order["status"] == OrderStatus.PREPARING

        ready_order = update_order_status(
            db=db_session,
            tenant_id=TENANT_ID,
            order_id=order_id,
            new_status=OrderStatus.READY,
        )

        assert ready_order["status"] == OrderStatus.READY

    cancelled_order = cancel_order(
        db=db_session,
        tenant_id=TENANT_ID,
        order_id=order_id,
    )

    assert cancelled_order["status"] == OrderStatus.CANCELLED
    assert cancelled_order["inventory_consumed_at"] is None

    history = get_order_status_history(
        db=db_session,
        order_id=order_id,
        tenant_id=TENANT_ID,
    )

    if preparation_status == OrderStatus.REGISTERED:
        assert len(history) == 2

        assert history[0].to_status == OrderStatus.REGISTERED.value
        assert history[1].to_status == OrderStatus.CANCELLED.value

    elif preparation_status == OrderStatus.PREPARING:
        assert len(history) == 3

        assert history[0].to_status == OrderStatus.REGISTERED.value
        assert history[1].to_status == OrderStatus.PREPARING.value
        assert history[2].to_status == OrderStatus.CANCELLED.value

    else:
        assert len(history) == 4

        assert history[0].to_status == OrderStatus.REGISTERED.value
        assert history[1].to_status == OrderStatus.PREPARING.value
        assert history[2].to_status == OrderStatus.READY.value
        assert history[3].to_status == OrderStatus.CANCELLED.value


def test_cancelled_order_cannot_be_cancelled_again(
    db_session: Session,
):
    """
    Verify that a cancelled order is a terminal state
    and cannot be cancelled again.
    """

    created_order = _create_test_order(db_session)
    order_id = created_order["id"]

    cancelled_order = cancel_order(
        db=db_session,
        tenant_id=TENANT_ID,
        order_id=order_id,
    )

    assert cancelled_order["status"] == OrderStatus.CANCELLED

    with pytest.raises(HTTPException) as exc_info:
        cancel_order(
            db=db_session,
            tenant_id=TENANT_ID,
            order_id=order_id,
        )

    assert exc_info.value.status_code == 400
    assert (
        exc_info.value.detail
        == "Order cannot be cancelled from status CANCELLED."
    )