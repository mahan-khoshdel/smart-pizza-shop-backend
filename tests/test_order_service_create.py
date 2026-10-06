from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.order import OrderStatus
from app.database.models.product_variant import ProductVariant
from app.schemas.order import OrderCreate
from app.services.order import (
    create_order,
    get_order_status_history,
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

NON_EXISTENT_BRANCH_ID = UUID(
    "00000000-0000-0000-0000-000000000010"
)

NON_EXISTENT_CUSTOMER_ID = UUID(
    "00000000-0000-0000-0000-000000000011"
)

NON_EXISTENT_ADDRESS_ID = UUID(
    "00000000-0000-0000-0000-000000000012"
)

NON_EXISTENT_PRODUCT_VARIANT_ID = UUID(
    "00000000-0000-0000-0000-000000000013"
)


def _build_order_data(
    *,
    order_type: str = "DINE_IN",
    customer_id=None,
    customer_address_id=None,
    items=None,
    order_number: str | None = None,
) -> OrderCreate:
    return OrderCreate(
        branch_id=BRANCH_ID,
        customer_id=customer_id,
        customer_address_id=customer_address_id,
        order_number=order_number or f"TEST-CREATE-{uuid4().hex[:8]}",
        order_type=order_type,
        note="Automated order creation test.",
        items=(
            items
            if items is not None
            else [
                {
                    "product_variant_id": PRODUCT_VARIANT_ID,
                    "quantity": 1,
                }
            ]
        ),
    )


def test_create_order_creates_registered_order(
    db_session: Session,
):
    order_data = _build_order_data()

    created_order = create_order(
        db=db_session,
        tenant_id=TENANT_ID,
        data=order_data,
    )

    assert created_order["tenant_id"] == TENANT_ID
    assert created_order["branch_id"] == BRANCH_ID
    assert created_order["order_number"] == order_data.order_number
    assert created_order["status"] == OrderStatus.REGISTERED
    assert created_order["customer_id"] is None
    assert created_order["items"]


def test_create_order_creates_initial_status_history(
    db_session: Session,
):
    order_data = _build_order_data()

    created_order = create_order(
        db=db_session,
        tenant_id=TENANT_ID,
        data=order_data,
    )

    history = get_order_status_history(
        db=db_session,
        order_id=created_order["id"],
        tenant_id=TENANT_ID,
    )

    assert len(history) == 1
    assert history[0].from_status is None
    assert history[0].to_status == OrderStatus.REGISTERED.value


def test_create_order_rejects_duplicate_order_number(
    db_session: Session,
):
    order_number = f"TEST-DUPLICATE-{uuid4().hex[:8]}"

    first_order_data = _build_order_data(
        order_number=order_number,
    )

    create_order(
        db=db_session,
        tenant_id=TENANT_ID,
        data=first_order_data,
    )

    duplicate_order_data = _build_order_data(
        order_number=order_number,
    )

    with pytest.raises(HTTPException) as exc_info:
        create_order(
            db=db_session,
            tenant_id=TENANT_ID,
            data=duplicate_order_data,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "Order number already exists."


def test_create_order_rejects_missing_branch(
    db_session: Session,
):
    order_data = _build_order_data()

    order_data = order_data.model_copy(
        update={
            "branch_id": NON_EXISTENT_BRANCH_ID,
        }
    )

    with pytest.raises(HTTPException) as exc_info:
        create_order(
            db=db_session,
            tenant_id=TENANT_ID,
            data=order_data,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Branch not found."


def test_create_order_rejects_branch_from_other_tenant(
    db_session: Session,
):
    order_data = _build_order_data()

    with pytest.raises(HTTPException) as exc_info:
        create_order(
            db=db_session,
            tenant_id=FAKE_OTHER_TENANT_ID,
            data=order_data,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Branch not found."


def test_create_order_rejects_missing_customer(
    db_session: Session,
):
    order_data = _build_order_data(
        customer_id=NON_EXISTENT_CUSTOMER_ID,
    )

    with pytest.raises(HTTPException) as exc_info:
        create_order(
            db=db_session,
            tenant_id=TENANT_ID,
            data=order_data,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Customer not found."


def test_create_delivery_order_requires_customer(
    db_session: Session,
):
    order_data = _build_order_data(
        order_type="DELIVERY",
        customer_id=None,
        customer_address_id=None,
    )

    with pytest.raises(HTTPException) as exc_info:
        create_order(
            db=db_session,
            tenant_id=TENANT_ID,
            data=order_data,
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == (
        "Delivery orders require a customer."
    )


def test_create_delivery_order_requires_customer_address(
    db_session: Session,
):
    order_data = _build_order_data(
        order_type="DELIVERY",
        customer_id=NON_EXISTENT_CUSTOMER_ID,
        customer_address_id=None,
    )

    with pytest.raises(HTTPException) as exc_info:
        create_order(
            db=db_session,
            tenant_id=TENANT_ID,
            data=order_data,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Customer not found."


def test_create_order_rejects_address_without_customer(
    db_session: Session,
):
    order_data = _build_order_data(
        customer_id=None,
        customer_address_id=NON_EXISTENT_ADDRESS_ID,
    )

    with pytest.raises(HTTPException) as exc_info:
        create_order(
            db=db_session,
            tenant_id=TENANT_ID,
            data=order_data,
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == (
        "Customer is required when address is provided."
    )


def test_create_order_requires_at_least_one_item(
    db_session: Session,
):
    order_data = _build_order_data(
        items=[],
    )

    with pytest.raises(HTTPException) as exc_info:
        create_order(
            db=db_session,
            tenant_id=TENANT_ID,
            data=order_data,
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == (
        "Order must contain at least one item."
    )


def test_create_order_rejects_missing_product_variant(
    db_session: Session,
):
    order_data = _build_order_data(
        items=[
            {
                "product_variant_id": NON_EXISTENT_PRODUCT_VARIANT_ID,
                "quantity": 1,
            }
        ],
    )

    with pytest.raises(HTTPException) as exc_info:
        create_order(
            db=db_session,
            tenant_id=TENANT_ID,
            data=order_data,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == (
        "Product variant not found: "
        f"{NON_EXISTENT_PRODUCT_VARIANT_ID}"
    )


def test_create_order_calculates_subtotal_from_variant_price(
    db_session: Session,
):
    product_variant = db_session.scalar(
        select(ProductVariant).where(
            ProductVariant.id == PRODUCT_VARIANT_ID,
            ProductVariant.tenant_id == TENANT_ID,
        )
    )

    assert product_variant is not None

    quantity = 3

    order_data = _build_order_data(
        items=[
            {
                "product_variant_id": PRODUCT_VARIANT_ID,
                "quantity": quantity,
            }
        ],
    )

    created_order = create_order(
        db=db_session,
        tenant_id=TENANT_ID,
        data=order_data,
    )

    expected_subtotal = (
        Decimal(str(product_variant.price))
        * quantity
    )

    assert created_order["subtotal"] == expected_subtotal
    assert created_order["discount_total"] == 0
    assert created_order["tax_total"] == 0
    assert created_order["total"] == expected_subtotal