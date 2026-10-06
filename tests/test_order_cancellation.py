from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.database.models.order import OrderStatus
from app.schemas.order import OrderCreate
from app.services.order import (
    cancel_order,
    create_order,
    update_order_status,
    get_order_status_history,
)


TENANT_ID = UUID(
    "25291ef5-0240-4042-aabc-b92c5aa4957a"
)

FAKE_OTHER_TENANT_ID = UUID(
    "00000000-0000-0000-0000-000000000001"
)

BRANCH_ID = UUID(
    "6146f071-baf4-40e9-bbff-71f86e0a7770"
)

PRODUCT_VARIANT_ID = UUID(
    "7c065b06-1422-446b-a163-d6a30b4b659b"
)

NON_EXISTENT_ORDER_ID = UUID(
    "00000000-0000-0000-0000-000000000099"
)


def _create_test_order(db: Session) -> dict:
    order_number = (
        f"TEST-CANCEL-{uuid4().hex[:8]}"
    )

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


def _move_order_to_status(
    db: Session,
    order_id,
    target_status: OrderStatus,
) -> None:
    if target_status == OrderStatus.REGISTERED:
        return

    preparing_order = update_order_status(
        db=db,
        tenant_id=TENANT_ID,
        order_id=order_id,
        new_status=OrderStatus.PREPARING,
    )

    assert (
        preparing_order["status"]
        == OrderStatus.PREPARING
    )

    if target_status == OrderStatus.PREPARING:
        return

    ready_order = update_order_status(
        db=db,
        tenant_id=TENANT_ID,
        order_id=order_id,
        new_status=OrderStatus.READY,
    )

    assert (
        ready_order["status"]
        == OrderStatus.READY
    )


@pytest.mark.parametrize(
    "current_status",
    [
        OrderStatus.REGISTERED,
        OrderStatus.PREPARING,
        OrderStatus.READY,
    ],
)
def test_order_can_be_cancelled_from_allowed_statuses(
    db_session,
    current_status: OrderStatus,
):
    created_order = _create_test_order(
        db_session,
    )

    order_id = created_order["id"]

    _move_order_to_status(
        db=db_session,
        order_id=order_id,
        target_status=current_status,
    )

    cancelled_order = cancel_order(
        db=db_session,
        tenant_id=TENANT_ID,
        order_id=order_id,
    )

    assert cancelled_order["id"] == order_id
    assert cancelled_order["tenant_id"] == TENANT_ID
    assert cancelled_order["branch_id"] == BRANCH_ID
    assert (
        cancelled_order["status"]
        == OrderStatus.CANCELLED
    )
    assert (
        cancelled_order["inventory_consumed_at"]
        is None
    )
    assert cancelled_order["items"]

    history = get_order_status_history(
        db=db_session,
        tenant_id=TENANT_ID,
        order_id=order_id,
    )

    expected_history = [
        OrderStatus.REGISTERED.value,
    ]

    if current_status == OrderStatus.PREPARING:
        expected_history.append(
            OrderStatus.PREPARING.value
        )

    elif current_status == OrderStatus.READY:
        expected_history.extend(
            [
                OrderStatus.PREPARING.value,
                OrderStatus.READY.value,
            ]
        )

    expected_history.append(
        OrderStatus.CANCELLED.value
    )

    actual_history = [
        history_item.to_status
        for history_item in history
    ]

    assert actual_history == expected_history


def test_cancelled_order_cannot_be_cancelled_again(
    db_session,
):
    created_order = _create_test_order(
        db_session,
    )

    order_id = created_order["id"]

    cancelled_order = cancel_order(
        db=db_session,
        tenant_id=TENANT_ID,
        order_id=order_id,
    )

    assert (
        cancelled_order["status"]
        == OrderStatus.CANCELLED
    )

    with pytest.raises(HTTPException) as exc_info:
        cancel_order(
            db=db_session,
            tenant_id=TENANT_ID,
            order_id=order_id,
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == (
        "Order cannot be cancelled from status "
        "CANCELLED."
    )


def test_completed_order_cannot_be_cancelled(
    db_session,
):
    created_order = _create_test_order(
        db_session,
    )

    order_id = created_order["id"]

    update_order_status(
        db=db_session,
        tenant_id=TENANT_ID,
        order_id=order_id,
        new_status=OrderStatus.PREPARING,
    )

    update_order_status(
        db=db_session,
        tenant_id=TENANT_ID,
        order_id=order_id,
        new_status=OrderStatus.READY,
    )

    completed_order = update_order_status(
        db=db_session,
        tenant_id=TENANT_ID,
        order_id=order_id,
        new_status=OrderStatus.COMPLETED,
    )

    assert (
        completed_order["status"]
        == OrderStatus.COMPLETED
    )
    assert (
        completed_order["inventory_consumed_at"]
        is not None
    )

    with pytest.raises(HTTPException) as exc_info:
        cancel_order(
            db=db_session,
            tenant_id=TENANT_ID,
            order_id=order_id,
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == (
        "Order cannot be cancelled from status "
        "COMPLETED."
    )


def test_cancel_order_is_tenant_scoped(
    db_session,
):
    created_order = _create_test_order(
        db_session,
    )

    order_id = created_order["id"]

    with pytest.raises(HTTPException) as exc_info:
        cancel_order(
            db=db_session,
            tenant_id=FAKE_OTHER_TENANT_ID,
            order_id=order_id,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == (
        "Order not found."
    )


def test_cancel_order_returns_404_for_missing_order(
    db_session,
):
    with pytest.raises(HTTPException) as exc_info:
        cancel_order(
            db=db_session,
            tenant_id=TENANT_ID,
            order_id=NON_EXISTENT_ORDER_ID,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == (
        "Order not found."
    )