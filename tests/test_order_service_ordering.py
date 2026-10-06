from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.database.models.order import Order, OrderStatus
from app.schemas.order import OrderCreate
from app.services.order import create_order, get_orders


TENANT_ID = UUID(
    "25291ef5-0240-4042-aabc-b92c5aa4957a"
)

BRANCH_ID = UUID(
    "6146f071-baf4-40e9-bbff-71f86e0a7770"
)

PRODUCT_VARIANT_ID = UUID(
    "7c065b06-1422-446b-a163-d6a30b4b659b"
)


def _create_order(
    db_session: Session,
    prefix: str,
) -> dict:
    order_data = OrderCreate(
        branch_id=BRANCH_ID,
        customer_id=None,
        customer_address_id=None,
        order_number=f"{prefix}-{uuid4().hex[:8]}",
        order_type="DINE_IN",
        note="Automated order ordering test.",
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


def test_get_orders_returns_newest_order_first(
    db_session: Session,
):
    older_order = _create_order(
        db_session,
        "TEST-ORDER-OLDER",
    )

    newer_order = _create_order(
        db_session,
        "TEST-ORDER-NEWER",
    )

    older_order_model = db_session.get(
        Order,
        older_order["id"],
    )

    newer_order_model = db_session.get(
        Order,
        newer_order["id"],
    )

    older_order_model.created_at = datetime(
        2026,
        10,
        6,
        10,
        0,
        0,
        tzinfo=timezone.utc,
    )

    newer_order_model.created_at = datetime(
        2026,
        10,
        6,
        10,
        5,
        0,
        tzinfo=timezone.utc,
    )

    db_session.flush()

    orders = get_orders(
        db=db_session,
        tenant_id=TENANT_ID,
    )

    assert orders[0]["id"] == newer_order["id"]
    assert orders[1]["id"] == older_order["id"]


def test_get_orders_keeps_newest_first_ordering(
    db_session: Session,
):
    first_order = _create_order(
        db_session,
        "TEST-ORDER-FIRST",
    )

    second_order = _create_order(
        db_session,
        "TEST-ORDER-SECOND",
    )

    third_order = _create_order(
        db_session,
        "TEST-ORDER-THIRD",
    )

    first_order_model = db_session.get(
        Order,
        first_order["id"],
    )

    second_order_model = db_session.get(
        Order,
        second_order["id"],
    )

    third_order_model = db_session.get(
        Order,
        third_order["id"],
    )

    first_order_model.created_at = datetime(
        2026,
        10,
        6,
        10,
        0,
        0,
        tzinfo=timezone.utc,
    )

    second_order_model.created_at = datetime(
        2026,
        10,
        6,
        10,
        5,
        0,
        tzinfo=timezone.utc,
    )

    third_order_model.created_at = datetime(
        2026,
        10,
        6,
        10,
        10,
        0,
        tzinfo=timezone.utc,
    )

    db_session.flush()

    orders = get_orders(
        db=db_session,
        tenant_id=TENANT_ID,
    )

    returned_ids = [
        order["id"]
        for order in orders
        if order["id"]
        in {
            first_order["id"],
            second_order["id"],
            third_order["id"],
        }
    ]

    assert returned_ids == [
        third_order["id"],
        second_order["id"],
        first_order["id"],
    ]

    assert all(
        order["status"] == OrderStatus.REGISTERED
        for order in orders
        if order["id"]
        in {
            first_order["id"],
            second_order["id"],
            third_order["id"],
        }
    )