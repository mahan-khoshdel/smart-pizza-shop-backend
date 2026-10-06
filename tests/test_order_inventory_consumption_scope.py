from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.schemas.order import OrderCreate
from app.services.order import (
    consume_order_inventory,
    create_order,
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

NON_EXISTENT_ORDER_ID = UUID(
    "00000000-0000-0000-0000-000000000099"
)


def _create_test_order(db: Session):
    """
    Create a unique registered order for scope tests.
    """

    order_number = (
        f"TEST-INVENTORY-SCOPE-"
        f"{uuid4().hex[:8]}"
    )

    order_data = OrderCreate(
        branch_id=BRANCH_ID,
        customer_id=None,
        customer_address_id=None,
        order_number=order_number,
        order_type="DINE_IN",
        note="Automated inventory scope test.",
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


def test_consume_order_inventory_returns_404_for_missing_order(
    db_session: Session,
):
    """
    Verify that inventory consumption returns 404
    when the requested order does not exist.
    """

    with pytest.raises(HTTPException) as exc_info:
        consume_order_inventory(
            db=db_session,
            tenant_id=TENANT_ID,
            order_id=NON_EXISTENT_ORDER_ID,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Order not found."


def test_consume_order_inventory_is_tenant_scoped(
    db_session: Session,
):
    """
    Verify that one tenant cannot access an order belonging
    to another tenant through inventory consumption.
    """

    created_order = _create_test_order(
        db=db_session,
    )

    with pytest.raises(HTTPException) as exc_info:
        consume_order_inventory(
            db=db_session,
            tenant_id=FAKE_OTHER_TENANT_ID,
            order_id=created_order["id"],
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Order not found."