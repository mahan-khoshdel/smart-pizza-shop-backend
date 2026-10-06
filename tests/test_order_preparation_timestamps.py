from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.order import Order, OrderStatus
from app.schemas.order import OrderCreate
from app.services.order import create_order, update_order_status


TENANT_ID = UUID(
    "25291ef5-0240-4042-aabc-b92c5aa4957a"
)

BRANCH_ID = UUID(
    "6146f071-baf4-40e9-bbff-71f86e0a7770"
)

PRODUCT_VARIANT_ID = UUID(
    "7c065b06-1422-446b-a163-d6a30b4b659b"
)


def _create_order(db: Session) -> dict:
    order_data = OrderCreate(
        branch_id=BRANCH_ID,
        customer_id=None,
        customer_address_id=None,
        order_number=f"TEST-TIMESTAMP-{uuid4().hex[:8]}",
        order_type="DINE_IN",
        note="Automated preparation timestamp test.",
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


def _get_order(db: Session, order_id):
    return db.scalar(
        select(Order).where(
            Order.id == order_id,
            Order.tenant_id == TENANT_ID,
        )
    )


def test_registered_order_has_no_preparation_timestamps(
    db_session: Session,
):
    created_order = _create_order(
        db=db_session,
    )

    order = _get_order(
        db=db_session,
        order_id=created_order["id"],
    )

    assert order is not None
    assert order.status == OrderStatus.REGISTERED
    assert order.preparing_at is None
    assert order.ready_at is None


def test_preparing_transition_sets_preparing_timestamp(
    db_session: Session,
):
    created_order = _create_order(
        db=db_session,
    )

    update_order_status(
        db=db_session,
        tenant_id=TENANT_ID,
        order_id=created_order["id"],
        new_status=OrderStatus.PREPARING,
    )

    order = _get_order(
        db=db_session,
        order_id=created_order["id"],
    )

    assert order is not None
    assert order.status == OrderStatus.PREPARING
    assert order.preparing_at is not None
    assert order.ready_at is None


def test_ready_transition_sets_ready_timestamp_after_preparing(
    db_session: Session,
):
    created_order = _create_order(
        db=db_session,
    )

    update_order_status(
        db=db_session,
        tenant_id=TENANT_ID,
        order_id=created_order["id"],
        new_status=OrderStatus.PREPARING,
    )

    preparing_order = _get_order(
        db=db_session,
        order_id=created_order["id"],
    )

    assert preparing_order is not None
    assert preparing_order.preparing_at is not None
    assert preparing_order.ready_at is None

    preparing_at = preparing_order.preparing_at

    update_order_status(
        db=db_session,
        tenant_id=TENANT_ID,
        order_id=created_order["id"],
        new_status=OrderStatus.READY,
    )

    ready_order = _get_order(
        db=db_session,
        order_id=created_order["id"],
    )

    assert ready_order is not None
    assert ready_order.status == OrderStatus.READY
    assert ready_order.preparing_at == preparing_at
    assert ready_order.ready_at is not None
    assert ready_order.ready_at >= ready_order.preparing_at