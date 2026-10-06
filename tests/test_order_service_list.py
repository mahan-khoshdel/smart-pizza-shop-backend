from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.database.models.order import OrderStatus
from app.schemas.order import OrderCreate
from app.services.order import (
    cancel_order,
    create_order,
    get_orders,
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


def _create_test_order(
    db: Session,
    prefix: str,
) -> dict:
    order_number = (
        f"{prefix}-{uuid4().hex[:8]}"
    )

    order_data = OrderCreate(
        branch_id=BRANCH_ID,
        customer_id=None,
        customer_address_id=None,
        order_number=order_number,
        order_type="DINE_IN",
        note="Automated order list service test.",
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


def test_get_orders_returns_current_tenant_orders(
    db_session,
):
    first_order = _create_test_order(
        db=db_session,
        prefix="TEST-LIST-A",
    )

    second_order = _create_test_order(
        db=db_session,
        prefix="TEST-LIST-B",
    )

    orders = get_orders(
        db=db_session,
        tenant_id=TENANT_ID,
    )

    order_ids = {
        order["id"]
        for order in orders
    }

    assert first_order["id"] in order_ids
    assert second_order["id"] in order_ids

    assert all(
        order["tenant_id"] == TENANT_ID
        for order in orders
    )


def test_get_orders_returns_order_items(
    db_session,
):
    created_order = _create_test_order(
        db=db_session,
        prefix="TEST-LIST-ITEMS",
    )

    orders = get_orders(
        db=db_session,
        tenant_id=TENANT_ID,
    )

    matching_orders = [
        order
        for order in orders
        if order["id"] == created_order["id"]
    ]

    assert len(matching_orders) == 1

    result = matching_orders[0]

    assert result["order_number"] == (
        created_order["order_number"]
    )

    assert result["status"] == (
        OrderStatus.REGISTERED
    )

    assert result["items"]
    assert len(result["items"]) == 1

    item = result["items"][0]

    assert (
        item.product_variant_id
        == PRODUCT_VARIANT_ID
    )
    assert item.quantity == 1


def test_get_orders_filters_by_status(
    db_session,
):
    registered_order = _create_test_order(
        db=db_session,
        prefix="TEST-LIST-REGISTERED",
    )

    cancelled_order = _create_test_order(
        db=db_session,
        prefix="TEST-LIST-CANCELLED",
    )

    cancel_order(
        db=db_session,
        tenant_id=TENANT_ID,
        order_id=cancelled_order["id"],
    )

    registered_orders = get_orders(
        db=db_session,
        tenant_id=TENANT_ID,
        status=OrderStatus.REGISTERED,
    )

    cancelled_orders = get_orders(
        db=db_session,
        tenant_id=TENANT_ID,
        status=OrderStatus.CANCELLED,
    )

    registered_ids = {
        order["id"]
        for order in registered_orders
    }

    cancelled_ids = {
        order["id"]
        for order in cancelled_orders
    }

    assert registered_order["id"] in registered_ids
    assert cancelled_order["id"] not in registered_ids

    assert cancelled_order["id"] in cancelled_ids
    assert registered_order["id"] not in cancelled_ids

    assert all(
        order["status"]
        == OrderStatus.REGISTERED
        for order in registered_orders
    )

    assert all(
        order["status"]
        == OrderStatus.CANCELLED
        for order in cancelled_orders
    )


def test_get_orders_does_not_return_other_tenant_orders(
    db_session,
):
    created_order = _create_test_order(
        db=db_session,
        prefix="TEST-LIST-TENANT",
    )

    current_tenant_orders = get_orders(
        db=db_session,
        tenant_id=TENANT_ID,
    )

    other_tenant_orders = get_orders(
        db=db_session,
        tenant_id=FAKE_OTHER_TENANT_ID,
    )

    current_ids = {
        order["id"]
        for order in current_tenant_orders
    }

    other_ids = {
        order["id"]
        for order in other_tenant_orders
    }

    assert created_order["id"] in current_ids
    assert created_order["id"] not in other_ids

    assert other_tenant_orders == []