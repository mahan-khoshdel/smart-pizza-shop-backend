from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.database.models.order import OrderStatus
from app.schemas.order import OrderCreate
from app.services.order import create_order, get_order


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


def _create_test_order(db: Session) -> dict:
    order_number = (
        f"TEST-ORDER-READ-{uuid4().hex[:8]}"
    )

    order_data = OrderCreate(
        branch_id=BRANCH_ID,
        customer_id=None,
        customer_address_id=None,
        order_number=order_number,
        order_type="DINE_IN",
        note="Automated order read service test.",
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


def test_get_order_returns_complete_order_data(db_session):
    created_order = _create_test_order(db_session)

    order_id = created_order["id"]

    result = get_order(
        db=db_session,
        tenant_id=TENANT_ID,
        order_id=order_id,
    )

    assert result["id"] == order_id
    assert result["tenant_id"] == TENANT_ID
    assert result["branch_id"] == BRANCH_ID
    assert result["order_number"] == created_order[
        "order_number"
    ]
    assert result["order_type"] == "DINE_IN"
    assert result["status"] == OrderStatus.REGISTERED
    assert (
        result["note"]
        == "Automated order read service test."
    )

    assert "items" in result
    assert result["items"]

    assert len(result["items"]) == 1

    item = result["items"][0]

    assert (
        item.product_variant_id
        == PRODUCT_VARIANT_ID
    )
    assert item.quantity == 1


def test_get_order_is_tenant_scoped(db_session):
    created_order = _create_test_order(db_session)

    order_id = created_order["id"]

    with pytest.raises(HTTPException) as exc_info:
        get_order(
            db=db_session,
            tenant_id=FAKE_OTHER_TENANT_ID,
            order_id=order_id,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Order not found."