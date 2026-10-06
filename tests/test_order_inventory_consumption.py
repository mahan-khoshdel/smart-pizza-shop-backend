from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.database.models.order import OrderStatus
from app.schemas.order import OrderCreate
from app.services.order import (
    consume_order_inventory,
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


def _create_test_order(db: Session):
    """
    Create a unique registered test order.
    """

    order_number = (
        f"TEST-INVENTORY-CONSUME-"
        f"{uuid4().hex[:8]}"
    )

    order_data = OrderCreate(
        branch_id=BRANCH_ID,
        customer_id=None,
        customer_address_id=None,
        order_number=order_number,
        order_type="DINE_IN",
        note="Automated inventory consumption test.",
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


def test_inventory_cannot_be_consumed_before_order_is_completed(
    db_session: Session,
):
    """
    Verify that inventory consumption is rejected
    for orders that are not COMPLETED.
    """

    created_order = _create_test_order(
        db=db_session,
    )

    assert created_order["status"] == OrderStatus.REGISTERED

    with pytest.raises(HTTPException) as exc_info:
        consume_order_inventory(
            db=db_session,
            tenant_id=TENANT_ID,
            order_id=created_order["id"],
        )

    assert exc_info.value.status_code == 400
    assert (
        exc_info.value.detail
        == "Inventory can only be consumed for completed orders."
    )


def test_inventory_cannot_be_consumed_twice_for_same_order(
    db_session: Session,
):
    """
    Verify that inventory consumption is idempotent
    and cannot happen twice for the same completed order.
    """

    created_order = _create_test_order(
        db=db_session,
    )

    order_id = created_order["id"]

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

    completed_order = update_order_status(
        db=db_session,
        tenant_id=TENANT_ID,
        order_id=order_id,
        new_status=OrderStatus.COMPLETED,
    )

    assert completed_order["status"] == OrderStatus.COMPLETED
    assert completed_order["inventory_consumed_at"] is not None

    with pytest.raises(HTTPException) as exc_info:
        consume_order_inventory(
            db=db_session,
            tenant_id=TENANT_ID,
            order_id=order_id,
        )

    assert exc_info.value.status_code == 409
    assert (
        exc_info.value.detail
        == "Inventory has already been consumed for this order."
    )