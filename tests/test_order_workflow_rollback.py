from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from app.database.models.order import OrderStatus
from app.repositories.order import OrderRepository
from app.schemas.order import OrderCreate
from app.services.order import (
    create_order,
    get_order_status_history,
    update_order_status,
)


TENANT_ID = UUID("25291ef5-0240-4042-aabc-b92c5aa4957a")

BRANCH_ID = UUID("6146f071-baf4-40e9-bbff-71f86e0a7770")

PRODUCT_VARIANT_ID = UUID(
    "7c065b06-1422-446b-a163-d6a30b4b659b"
)


def _get_history_status(history_item, field_name: str):
    """
    Return a status-history field from either
    an ORM object or a dictionary-like result.
    """
    if hasattr(history_item, field_name):
        return getattr(history_item, field_name)

    return history_item[field_name]


def test_order_completion_rolls_back_when_inventory_is_insufficient(
    db_session,
):
    """
    Verify that completing an order is atomic.

    When inventory consumption fails:
    - the order must remain READY
    - inventory_consumed_at must remain None
    - READY -> COMPLETED history must not be created
    - the transaction must be rolled back
    """

    # ---------------------------------------------------------
    # 1. Create a deliberately huge order
    # ---------------------------------------------------------

    order_number = f"TEST-ROLLBACK-{uuid4().hex[:8]}"

    order_data = OrderCreate(
        branch_id=BRANCH_ID,
        customer_id=None,
        customer_address_id=None,
        order_number=order_number,
        order_type="DINE_IN",
        note="Automated inventory rollback test order.",
        items=[
            {
                "product_variant_id": PRODUCT_VARIANT_ID,
                "quantity": 1_000_000_000,
            }
        ],
    )

    created_order = create_order(
        db=db_session,
        tenant_id=TENANT_ID,
        data=order_data,
    )

    order_id = created_order["id"]

    assert created_order["status"] == OrderStatus.REGISTERED

    # ---------------------------------------------------------
    # 2. REGISTERED -> PREPARING
    # ---------------------------------------------------------

    preparing_order = update_order_status(
        db=db_session,
        tenant_id=TENANT_ID,
        order_id=order_id,
        new_status=OrderStatus.PREPARING,
    )

    assert preparing_order["status"] == OrderStatus.PREPARING

    # ---------------------------------------------------------
    # 3. PREPARING -> READY
    # ---------------------------------------------------------

    ready_order = update_order_status(
        db=db_session,
        tenant_id=TENANT_ID,
        order_id=order_id,
        new_status=OrderStatus.READY,
    )

    assert ready_order["status"] == OrderStatus.READY
    assert ready_order["inventory_consumed_at"] is None

    # ---------------------------------------------------------
    # 4. READY -> COMPLETED must fail because of inventory
    # ---------------------------------------------------------

    with pytest.raises(HTTPException) as exc_info:
        update_order_status(
            db=db_session,
            tenant_id=TENANT_ID,
            order_id=order_id,
            new_status=OrderStatus.COMPLETED,
        )

    assert exc_info.value.status_code in {400, 409}

    # ---------------------------------------------------------
    # 5. Refresh ORM state after rollback
    # ---------------------------------------------------------

    db_session.expire_all()

    repository = OrderRepository(db_session)

    stored_order = repository.get_by_id(
        order_id=order_id,
        tenant_id=TENANT_ID,
    )

    assert stored_order is not None

    # The failed transaction must not complete the order.
    assert stored_order.status == OrderStatus.READY

    # Inventory must not be marked as consumed.
    assert stored_order.inventory_consumed_at is None

    # ---------------------------------------------------------
    # 6. Verify status history
    # ---------------------------------------------------------

    history = get_order_status_history(
        db=db_session,
        order_id=order_id,
        tenant_id=TENANT_ID,
    )

    history_transitions = {
        (
            _get_history_status(item, "from_status"),
            _get_history_status(item, "to_status"),
        )
        for item in history
    }

    expected_transitions = {
        (
            None,
            OrderStatus.REGISTERED.value,
        ),
        (
            OrderStatus.REGISTERED.value,
            OrderStatus.PREPARING.value,
        ),
        (
            OrderStatus.PREPARING.value,
            OrderStatus.READY.value,
        ),
    }

    assert history_transitions == expected_transitions