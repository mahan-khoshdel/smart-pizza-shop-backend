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
    order_data = OrderCreate(
        branch_id=BRANCH_ID,
        customer_id=None,
        customer_address_id=None,
        order_number=f"TEST-HISTORY-{uuid4().hex[:8]}",
        order_type="DINE_IN",
        note="Automated status history test.",
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


def test_get_order_status_history_returns_initial_history(
    db_session: Session,
):
    created_order = _create_test_order(
        db=db_session,
    )

    history = get_order_status_history(
        db=db_session,
        order_id=created_order["id"],
        tenant_id=TENANT_ID,
    )

    assert len(history) == 1
    assert history[0].from_status is None
    assert history[0].to_status == OrderStatus.REGISTERED.value
    assert history[0].order_id == created_order["id"]


def test_get_order_status_history_reflects_order_cancellation(
    db_session: Session,
):
    created_order = _create_test_order(
        db=db_session,
    )

    cancelled_order = cancel_order(
        db=db_session,
        tenant_id=TENANT_ID,
        order_id=created_order["id"],
    )

    assert cancelled_order["status"] == OrderStatus.CANCELLED

    history = get_order_status_history(
        db=db_session,
        order_id=created_order["id"],
        tenant_id=TENANT_ID,
    )

    assert len(history) == 2

    statuses = {
        history_item.to_status
        for history_item in history
    }

    assert statuses == {
        OrderStatus.REGISTERED.value,
        OrderStatus.CANCELLED.value,
    }

    cancellation_history = [
        item
        for item in history
        if item.to_status == OrderStatus.CANCELLED.value
    ]

    assert len(cancellation_history) == 1
    assert (
        cancellation_history[0].from_status
        == OrderStatus.REGISTERED.value
    )


def test_get_order_status_history_rejects_missing_order(
    db_session: Session,
):
    with pytest.raises(HTTPException) as exc_info:
        get_order_status_history(
            db=db_session,
            order_id=NON_EXISTENT_ORDER_ID,
            tenant_id=TENANT_ID,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Order not found."


def test_get_order_status_history_rejects_other_tenant(
    db_session: Session,
):
    created_order = _create_test_order(
        db=db_session,
    )

    with pytest.raises(HTTPException) as exc_info:
        get_order_status_history(
            db=db_session,
            order_id=created_order["id"],
            tenant_id=FAKE_OTHER_TENANT_ID,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Order not found."