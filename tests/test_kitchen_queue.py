from uuid import UUID, uuid4

import pytest

from app.database.models.order import OrderStatus
from app.repositories.order import OrderRepository
from app.schemas.order import OrderCreate
from app.services.order import create_order, get_kitchen_queue, update_order_status


TENANT_ID = UUID(
    "25291ef5-0240-4042-aabc-b92c5aa4957a"
)

BRANCH_ID = UUID(
    "6146f071-baf4-40e9-bbff-71f86e0a7770"
)

FAKE_OTHER_TENANT_ID = UUID(
    "00000000-0000-0000-0000-000000000001"
)

FAKE_OTHER_BRANCH_ID = UUID(
    "00000000-0000-0000-0000-000000000002"
)

PRODUCT_VARIANT_ID = UUID(
    "7c065b06-1422-446b-a163-d6a30b4b659b"
)


def _create_order(db_session):
    """
    Create a fresh REGISTERED order for kitchen queue tests.
    """

    order_data = OrderCreate(
        branch_id=BRANCH_ID,
        customer_id=None,
        customer_address_id=None,
        order_number=f"TEST-QUEUE-{uuid4().hex[:8]}",
        order_type="DINE_IN",
        note="Kitchen queue automated test.",
        items=[
            {
                "product_variant_id": PRODUCT_VARIANT_ID,
                "quantity": 1,
            }
        ],
    )

    return create_order(
        db=db_session,
        tenant_id=TENANT_ID,
        data=order_data,
    )


def test_kitchen_queue_returns_preparing_orders_with_positions(
    db_session,
    monkeypatch,
):
    """
    Verify that PREPARING orders appear in the kitchen queue
    with sequential queue positions.
    """

    def fake_get_kitchen_workload(
        self,
        tenant_id,
        branch_id,
    ):
        return {
            "preparing_count": 0,
            "ready_count": 0,
            "active_count": 0,
        }

    monkeypatch.setattr(
        OrderRepository,
        "get_kitchen_workload",
        fake_get_kitchen_workload,
    )

    first_order = _create_order(db_session)
    second_order = _create_order(db_session)

    update_order_status(
        db=db_session,
        tenant_id=TENANT_ID,
        order_id=first_order["id"],
        new_status=OrderStatus.PREPARING,
    )

    update_order_status(
        db=db_session,
        tenant_id=TENANT_ID,
        order_id=second_order["id"],
        new_status=OrderStatus.PREPARING,
    )

    queue = get_kitchen_queue(
        db=db_session,
        tenant_id=TENANT_ID,
        branch_id=BRANCH_ID,
    )

    assert queue["branch_id"] == BRANCH_ID
    assert queue["total_preparing"] >= 2

    queue_items = queue["queue"]

    test_items = [
        item
        for item in queue_items
        if item["order_id"]
        in {
            first_order["id"],
            second_order["id"],
        }
    ]

    assert len(test_items) == 2

    positions = sorted(
        item["queue_position"]
        for item in test_items
    )

    assert positions[1] == positions[0] + 1

    assert all(
        item["status"] == OrderStatus.PREPARING.value
        for item in test_items
    )


def test_kitchen_queue_rejects_other_tenant_context(
    db_session,
):
    """
    Verify that another tenant cannot access
    this tenant's kitchen queue.
    """

    repository = OrderRepository(db_session)

    queue = repository.get_kitchen_queue(
        tenant_id=FAKE_OTHER_TENANT_ID,
        branch_id=BRANCH_ID,
    )

    assert queue == []


def test_kitchen_queue_rejects_other_branch_context(
    db_session,
):
    """
    Verify that another branch cannot access
    this branch's kitchen queue.
    """

    repository = OrderRepository(db_session)

    queue = repository.get_kitchen_queue(
        tenant_id=TENANT_ID,
        branch_id=FAKE_OTHER_BRANCH_ID,
    )

    assert queue == []