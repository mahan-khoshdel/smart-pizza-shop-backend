from uuid import UUID, uuid4

from app.schemas.order import OrderCreate
from app.services.order import (
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

FAKE_BRANCH_ID = UUID(
    "00000000-0000-0000-0000-000000000002"
)

PRODUCT_VARIANT_ID = UUID(
    "7c065b06-1422-446b-a163-d6a30b4b659b"
)


def _create_order(db_session):
    order_data = OrderCreate(
        branch_id=BRANCH_ID,
        customer_id=None,
        customer_address_id=None,
        order_number=(
            f"TEST-SERVICE-BRANCH-"
            f"{uuid4().hex[:8]}"
        ),
        order_type="DINE_IN",
        note="Automated service branch filter test.",
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


def test_get_orders_filters_by_branch(
    db_session,
):
    created_order = _create_order(db_session)

    orders = get_orders(
        db=db_session,
        tenant_id=TENANT_ID,
        branch_id=BRANCH_ID,
    )

    returned_ids = {
        order["id"]
        for order in orders
    }

    assert created_order["id"] in returned_ids

    for order in orders:
        assert order["tenant_id"] == TENANT_ID
        assert order["branch_id"] == BRANCH_ID


def test_get_orders_branch_filter_excludes_other_branches(
    db_session,
):
    created_order = _create_order(db_session)

    orders = get_orders(
        db=db_session,
        tenant_id=TENANT_ID,
        branch_id=FAKE_BRANCH_ID,
    )

    returned_ids = {
        order["id"]
        for order in orders
    }

    assert created_order["id"] not in returned_ids

    for order in orders:
        assert order["branch_id"] == FAKE_BRANCH_ID


def test_get_orders_branch_filter_remains_tenant_scoped(
    db_session,
):
    created_order = _create_order(db_session)

    orders = get_orders(
        db=db_session,
        tenant_id=FAKE_OTHER_TENANT_ID,
        branch_id=BRANCH_ID,
    )

    returned_ids = {
        order["id"]
        for order in orders
    }

    assert created_order["id"] not in returned_ids

    for order in orders:
        assert order["tenant_id"] == FAKE_OTHER_TENANT_ID
        assert order["branch_id"] == BRANCH_ID