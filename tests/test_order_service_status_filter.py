from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from app.database.models.order import OrderStatus
from app.repositories.order import OrderRepository
from app.schemas.order import OrderCreate
from app.services.order import create_order, get_orders, update_order_status


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


def _create_order(
    db_session: Session,
) -> dict:
    order_data = OrderCreate(
        branch_id=BRANCH_ID,
        customer_id=None,
        customer_address_id=None,
        order_number=f"TEST-STATUS-FILTER-{uuid4().hex[:8]}",
        order_type="DINE_IN",
        note="Automated order status filter test.",
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


def test_get_orders_without_status_returns_orders_for_current_tenant(
    db_session: Session,
):
    created_order = _create_order(db_session)

    orders = get_orders(
        db=db_session,
        tenant_id=TENANT_ID,
    )

    order_ids = {order["id"] for order in orders}

    assert created_order["id"] in order_ids

    for order in orders:
        assert order["tenant_id"] == TENANT_ID


def test_get_orders_filters_by_registered_status(
    db_session: Session,
):
    created_order = _create_order(db_session)

    orders = get_orders(
        db=db_session,
        tenant_id=TENANT_ID,
        status=OrderStatus.REGISTERED,
    )

    matching_order = next(
        order
        for order in orders
        if order["id"] == created_order["id"]
    )

    assert matching_order["status"] == OrderStatus.REGISTERED

    for order in orders:
        assert order["status"] == OrderStatus.REGISTERED


def test_get_orders_filters_by_preparing_status(
    db_session: Session,
    monkeypatch,
):
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

    created_order = _create_order(db_session)

    update_order_status(
        db=db_session,
        tenant_id=TENANT_ID,
        order_id=created_order["id"],
        new_status=OrderStatus.PREPARING,
    )

    orders = get_orders(
        db=db_session,
        tenant_id=TENANT_ID,
        status=OrderStatus.PREPARING,
    )

    matching_order = next(
        order
        for order in orders
        if order["id"] == created_order["id"]
    )

    assert matching_order["status"] == OrderStatus.PREPARING

    for order in orders:
        assert order["status"] == OrderStatus.PREPARING


def test_get_orders_is_tenant_scoped(
    db_session: Session,
):
    created_order = _create_order(db_session)

    orders = get_orders(
        db=db_session,
        tenant_id=FAKE_OTHER_TENANT_ID,
    )

    order_ids = {order["id"] for order in orders}

    assert created_order["id"] not in order_ids

    for order in orders:
        assert order["tenant_id"] == FAKE_OTHER_TENANT_ID