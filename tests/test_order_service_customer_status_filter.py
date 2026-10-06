from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.customer import Customer
from app.schemas.order import OrderCreate, OrderStatus
from app.services.order import (
    cancel_order,
    create_order,
    get_orders,
)


TENANT_ID = UUID("25291ef5-0240-4042-aabc-b92c5aa4957a")
FAKE_OTHER_TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")
BRANCH_ID = UUID("6146f071-baf4-40e9-bbff-71f86e0a7770")
PRODUCT_VARIANT_ID = UUID("7c065b06-1422-446b-a163-d6a30b4b659b")


def _get_existing_customer_id(db_session: Session) -> UUID:
    customer_id = db_session.scalar(
        select(Customer.id).where(
            Customer.tenant_id == TENANT_ID
        )
    )

    assert customer_id is not None

    return customer_id


def _create_order(
    db_session: Session,
    customer_id: UUID | None,
) -> dict:
    order_data = OrderCreate(
        branch_id=BRANCH_ID,
        customer_id=customer_id,
        customer_address_id=None,
        order_number=f"TEST-CUSTOMER-STATUS-{uuid4().hex[:8]}",
        order_type="DINE_IN",
        note="Automated customer/status filter test.",
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


def test_get_orders_combined_customer_and_status_filter(
    db_session: Session,
):
    customer_id = _get_existing_customer_id(db_session)

    registered_order = _create_order(
        db_session,
        customer_id,
    )

    cancelled_order = _create_order(
        db_session,
        customer_id,
    )

    cancel_order(
        db=db_session,
        tenant_id=TENANT_ID,
        order_id=cancelled_order["id"],
    )

    orders = get_orders(
        db=db_session,
        tenant_id=TENANT_ID,
        status=OrderStatus.REGISTERED,
        customer_id=customer_id,
    )

    returned_ids = {
        order["id"]
        for order in orders
    }

    assert registered_order["id"] in returned_ids
    assert cancelled_order["id"] not in returned_ids

    for order in orders:
        assert order["tenant_id"] == TENANT_ID
        assert order["customer_id"] == customer_id
        assert order["status"] == OrderStatus.REGISTERED


def test_get_orders_customer_and_cancelled_status_filter(
    db_session: Session,
):
    customer_id = _get_existing_customer_id(db_session)

    registered_order = _create_order(
        db_session,
        customer_id,
    )

    cancelled_order = _create_order(
        db_session,
        customer_id,
    )

    cancel_order(
        db=db_session,
        tenant_id=TENANT_ID,
        order_id=cancelled_order["id"],
    )

    orders = get_orders(
        db=db_session,
        tenant_id=TENANT_ID,
        status=OrderStatus.CANCELLED,
        customer_id=customer_id,
    )

    returned_ids = {
        order["id"]
        for order in orders
    }

    assert cancelled_order["id"] in returned_ids
    assert registered_order["id"] not in returned_ids

    for order in orders:
        assert order["customer_id"] == customer_id
        assert order["status"] == OrderStatus.CANCELLED


def test_get_orders_combined_filters_remain_tenant_scoped(
    db_session: Session,
):
    customer_id = _get_existing_customer_id(db_session)

    order = _create_order(
        db_session,
        customer_id,
    )

    orders = get_orders(
        db=db_session,
        tenant_id=FAKE_OTHER_TENANT_ID,
        status=OrderStatus.REGISTERED,
        customer_id=customer_id,
    )

    returned_ids = {
        item["id"]
        for item in orders
    }

    assert order["id"] not in returned_ids

    for item in orders:
        assert item["tenant_id"] == FAKE_OTHER_TENANT_ID
        assert item["customer_id"] == customer_id
        assert item["status"] == OrderStatus.REGISTERED