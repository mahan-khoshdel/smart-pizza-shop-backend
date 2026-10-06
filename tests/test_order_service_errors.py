from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.database.models.order import OrderStatus
from app.repositories.order import OrderRepository
from app.schemas.order import OrderCreate
from app.services.order import (
    cancel_order,
    create_order,
    get_order,
    get_order_status_history,
    update_order_status,
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


def _create_registered_order(db: Session) -> dict:
    """
    Create a fresh REGISTERED order for service-level tests.
    """

    order_number = f"TEST-INVALID-TRANSITION-{uuid4().hex[:8]}"

    order_data = OrderCreate(
        branch_id=BRANCH_ID,
        customer_id=None,
        customer_address_id=None,
        order_number=order_number,
        order_type="DINE_IN",
        note="Automated invalid transition test.",
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


def test_get_order_raises_404_for_missing_order(
    db_session: Session,
):
    """
    Verify that requesting a missing order returns 404.
    """

    with pytest.raises(HTTPException) as exc_info:
        get_order(
            db=db_session,
            tenant_id=TENANT_ID,
            order_id=NON_EXISTENT_ORDER_ID,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Order not found."


def test_get_order_rejects_other_tenant(
    db_session: Session,
):
    """
    Verify that an order cannot be retrieved through
    another tenant context.
    """

    created_order = _create_registered_order(
        db=db_session,
    )

    with pytest.raises(HTTPException) as exc_info:
        get_order(
            db=db_session,
            tenant_id=FAKE_OTHER_TENANT_ID,
            order_id=created_order["id"],
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Order not found."


def test_update_order_status_raises_404_for_missing_order(
    db_session: Session,
):
    """
    Verify that updating a missing order returns 404.
    """

    with pytest.raises(HTTPException) as exc_info:
        update_order_status(
            db=db_session,
            tenant_id=TENANT_ID,
            order_id=NON_EXISTENT_ORDER_ID,
            new_status=OrderStatus.PREPARING,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Order not found."


def test_update_order_status_rejects_same_status(
    db_session: Session,
):
    """
    Verify that an order cannot be changed to its current status.
    """

    repository = OrderRepository(db_session)

    orders = repository.get_all(
        tenant_id=TENANT_ID,
    )

    assert orders

    order = orders[0]

    with pytest.raises(HTTPException) as exc_info:
        update_order_status(
            db=db_session,
            tenant_id=TENANT_ID,
            order_id=order.id,
            new_status=order.status,
        )

    assert exc_info.value.status_code == 400
    assert (
        f"{order.status.value} -> {order.status.value}"
        in exc_info.value.detail
    )


def test_update_order_status_rejects_other_tenant(
    db_session: Session,
):
    """
    Verify that another tenant cannot update the order status.
    """

    created_order = _create_registered_order(
        db=db_session,
    )

    with pytest.raises(HTTPException) as exc_info:
        update_order_status(
            db=db_session,
            tenant_id=FAKE_OTHER_TENANT_ID,
            order_id=created_order["id"],
            new_status=OrderStatus.PREPARING,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Order not found."


def test_order_status_history_rejects_other_tenant(
    db_session: Session,
):
    """
    Verify that order status history cannot be accessed
    through another tenant context.
    """

    repository = OrderRepository(db_session)

    orders = repository.get_all(
        tenant_id=TENANT_ID,
    )

    assert orders

    order = orders[0]

    with pytest.raises(HTTPException) as exc_info:
        get_order_status_history(
            db=db_session,
            order_id=order.id,
            tenant_id=FAKE_OTHER_TENANT_ID,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Order not found."


@pytest.mark.parametrize(
    "invalid_status",
    [
        OrderStatus.READY,
        OrderStatus.COMPLETED,
    ],
)
def test_registered_order_rejects_invalid_status_jump(
    db_session: Session,
    invalid_status: OrderStatus,
):
    """
    Verify that a REGISTERED order cannot skip required workflow stages.
    """

    created_order = _create_registered_order(
        db=db_session,
    )

    assert created_order["status"] == OrderStatus.REGISTERED

    with pytest.raises(HTTPException) as exc_info:
        update_order_status(
            db=db_session,
            tenant_id=TENANT_ID,
            order_id=created_order["id"],
            new_status=invalid_status,
        )

    assert exc_info.value.status_code == 400
    assert (
        exc_info.value.detail
        == (
            "Invalid status transition: "
            f"REGISTERED -> {invalid_status.value}."
        )
    )


def test_cancelled_order_rejects_new_status_transition(
    db_session: Session,
):
    """
    Verify that a cancelled order cannot re-enter the workflow.
    """

    created_order = _create_registered_order(
        db=db_session,
    )

    cancelled_order = cancel_order(
        db=db_session,
        tenant_id=TENANT_ID,
        order_id=created_order["id"],
    )

    assert cancelled_order["status"] == OrderStatus.CANCELLED

    with pytest.raises(HTTPException) as exc_info:
        update_order_status(
            db=db_session,
            tenant_id=TENANT_ID,
            order_id=created_order["id"],
            new_status=OrderStatus.PREPARING,
        )

    assert exc_info.value.status_code == 400
    assert (
        exc_info.value.detail
        == "Invalid status transition: CANCELLED -> PREPARING."
    )


def test_registered_order_rejects_preparing_when_kitchen_is_at_capacity(
    db_session: Session,
    monkeypatch,
):
    """
    Verify that a REGISTERED order cannot move to PREPARING
    when the kitchen has already reached its capacity.
    """

    def fake_get_kitchen_workload(
        self,
        tenant_id,
        branch_id,
    ):
        return {
            "preparing_count": 999,
            "ready_count": 0,
            "active_count": 999,
        }

    monkeypatch.setattr(
        OrderRepository,
        "get_kitchen_workload",
        fake_get_kitchen_workload,
    )

    created_order = _create_registered_order(
        db=db_session,
    )

    assert created_order["status"] == OrderStatus.REGISTERED

    with pytest.raises(HTTPException) as exc_info:
        update_order_status(
            db=db_session,
            tenant_id=TENANT_ID,
            order_id=created_order["id"],
            new_status=OrderStatus.PREPARING,
        )

    assert exc_info.value.status_code == 409
    assert (
        exc_info.value.detail
        == "Kitchen capacity reached. Preparing orders: 999. "
        f"Kitchen capacity: 8."
    )