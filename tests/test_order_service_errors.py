from uuid import UUID

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.database.models.order import OrderStatus
from app.repositories.order import OrderRepository
from app.services.order import get_order, update_order_status


TENANT_ID = UUID("25291ef5-0240-4042-aabc-b92c5aa4957a")

NON_EXISTENT_ORDER_ID = UUID(
    "00000000-0000-0000-0000-000000000099"
)


def test_get_order_raises_404_for_missing_order(
    db_session: Session,
):
    with pytest.raises(HTTPException) as exc_info:
        get_order(
            db=db_session,
            tenant_id=TENANT_ID,
            order_id=NON_EXISTENT_ORDER_ID,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Order not found."


def test_update_order_status_rejects_same_status(
    db_session: Session,
):
    repository = OrderRepository(db_session)

    orders = repository.get_all(
        tenant_id=TENANT_ID,
    )

    assert orders, "Expected at least one order for the test tenant."

    order = orders[0]

    with pytest.raises(HTTPException) as exc_info:
        update_order_status(
            db=db_session,
            tenant_id=TENANT_ID,
            order_id=order.id,
            new_status=order.status,
        )

    assert exc_info.value.status_code == 400
    assert (
        f"{order.status.value} -> {order.status.value}"
        in exc_info.value.detail
    )