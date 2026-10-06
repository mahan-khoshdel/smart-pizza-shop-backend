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
)


TENANT_ID = UUID(
    "25291ef5-0240-4042-aabc-b92c5aa4957a"
)

BRANCH_ID = UUID(
    "6146f071-baf4-40e9-bbff-71f86e0a7770"
)

PRODUCT_VARIANT_ID = UUID(
    "7c065b06-1422-446b-a163-d6a30b4b659b"
)


def _create_test_order(db: Session) -> dict:
    order_number = (
        f"TEST-TRANSITION-{uuid4().hex[:8]}"
    )

    order_data = OrderCreate(
        branch_id=BRANCH_ID,
        customer_id=None,
        customer_address_id=None,
        order_number=order_number,
        order_type="DINE_IN",
        note="Automated status transition test.",
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


def _assert_invalid_transition(
    db: Session,
    order_id,
    current_status: OrderStatus,
    invalid_status: OrderStatus,
) -> None:
    if current_status == OrderStatus.PREPARING:
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

    elif current_status == OrderStatus.READY:
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

    elif current_status == OrderStatus.CANCELLED:
        cancelled_order = cancel_order(
            db=db,
            tenant_id=TENANT_ID,
            order_id=order_id,
        )

        assert (
            cancelled_order["status"]
            == OrderStatus.CANCELLED
        )

    elif current_status == OrderStatus.COMPLETED:
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

        completed_order = update_order_status(
            db=db,
            tenant_id=TENANT_ID,
            order_id=order_id,
            new_status=OrderStatus.COMPLETED,
        )

        assert (
            completed_order["status"]
            == OrderStatus.COMPLETED
        )

    with pytest.raises(HTTPException) as exc_info:
        update_order_status(
            db=db,
            tenant_id=TENANT_ID,
            order_id=order_id,
            new_status=invalid_status,
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == (
        f"Invalid status transition: "
        f"{current_status.value} -> "
        f"{invalid_status.value}."
    )


def test_registered_cannot_transition_to_ready(
    db_session,
):
    order = _create_test_order(db_session)

    assert (
        order["status"]
        == OrderStatus.REGISTERED
    )

    _assert_invalid_transition(
        db=db_session,
        order_id=order["id"],
        current_status=OrderStatus.REGISTERED,
        invalid_status=OrderStatus.READY,
    )


def test_registered_cannot_transition_to_completed(
    db_session,
):
    order = _create_test_order(db_session)

    assert (
        order["status"]
        == OrderStatus.REGISTERED
    )

    _assert_invalid_transition(
        db=db_session,
        order_id=order["id"],
        current_status=OrderStatus.REGISTERED,
        invalid_status=OrderStatus.COMPLETED,
    )


def test_preparing_cannot_transition_to_completed(
    db_session,
):
    order = _create_test_order(db_session)

    _assert_invalid_transition(
        db=db_session,
        order_id=order["id"],
        current_status=OrderStatus.PREPARING,
        invalid_status=OrderStatus.COMPLETED,
    )


def test_ready_cannot_transition_back_to_preparing(
    db_session,
):
    order = _create_test_order(db_session)

    _assert_invalid_transition(
        db=db_session,
        order_id=order["id"],
        current_status=OrderStatus.READY,
        invalid_status=OrderStatus.PREPARING,
    )


def test_completed_cannot_transition_to_ready(
    db_session,
):
    order = _create_test_order(db_session)

    _assert_invalid_transition(
        db=db_session,
        order_id=order["id"],
        current_status=OrderStatus.COMPLETED,
        invalid_status=OrderStatus.READY,
    )


def test_cancelled_cannot_transition_to_preparing(
    db_session,
):
    order = _create_test_order(db_session)

    _assert_invalid_transition(
        db=db_session,
        order_id=order["id"],
        current_status=OrderStatus.CANCELLED,
        invalid_status=OrderStatus.PREPARING,
    )