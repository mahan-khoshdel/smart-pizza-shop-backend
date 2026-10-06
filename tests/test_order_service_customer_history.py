from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.customer import Customer
from app.schemas.order import OrderCreate
from app.services.order import create_order, get_orders


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


def _get_existing_customer_id(
    db_session: Session,
) -> UUID:
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
        order_number=(
            f"TEST-CUSTOMER-HISTORY-"
            f"{uuid4().hex[:8]}"
        ),
        order_type="DINE_IN",
        note="Automated customer history test.",
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


def test_get_orders_filters_by_customer(
    db_session: Session,
):
    customer_id = _get_existing_customer_id(
        db_session
    )

    customer_order = _create_order(
        db_session,
        customer_id,
    )

    anonymous_order = _create_order(
        db_session,
        None,
    )

    orders = get_orders(
        db=db_session,
        tenant_id=TENANT_ID,
        customer_id=customer_id,
    )

    order_ids = {
        order["id"]
        for order in orders
    }

    assert customer_order["id"] in order_ids
    assert anonymous_order["id"] not in order_ids

    for order in orders:
        assert order["customer_id"] == customer_id


def test_customer_order_history_remains_tenant_scoped(
    db_session: Session,
):
    customer_id = _get_existing_customer_id(
        db_session
    )

    customer_order = _create_order(
        db_session,
        customer_id,
    )

    orders = get_orders(
        db=db_session,
        tenant_id=FAKE_OTHER_TENANT_ID,
        customer_id=customer_id,
    )

    order_ids = {
        order["id"]
        for order in orders
    }

    assert customer_order["id"] not in order_ids

    for order in orders:
        assert order["tenant_id"] == FAKE_OTHER_TENANT_ID