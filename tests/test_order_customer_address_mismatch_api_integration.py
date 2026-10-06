"""
Integration tests for customer/address ownership validation.
"""

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect as sa_inspect
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_data
from app.core.dependencies import get_db as core_get_db
from app.database.connection import get_db as connection_get_db
from app.database.models.customer import Customer
from app.database.models.customer_address import CustomerAddress
from app.main import app


TENANT_ID = UUID(
    "25291ef5-0240-4042-aabc-b92c5aa4957a"
)

USER_ID = UUID(
    "00000000-0000-0000-0000-000000000010"
)

BRANCH_ID = UUID(
    "6146f071-baf4-40e9-bbff-71f86e0a7770"
)

PRODUCT_VARIANT_ID = UUID(
    "7c065b06-1422-446b-a163-d6a30b4b659b"
)


@pytest.fixture
def authenticated_client(
    db_session: Session,
):
    """
    Provide an authenticated API client backed by
    the real PostgreSQL test session.
    """
    original_overrides = (
        app.dependency_overrides.copy()
    )

    def override_current_user():
        return {
            "user_id": USER_ID,
            "tenant_id": TENANT_ID,
        }

    def override_get_db():
        yield db_session

    app.dependency_overrides[
        get_current_user_data
    ] = override_current_user

    app.dependency_overrides[
        connection_get_db
    ] = override_get_db

    app.dependency_overrides[
        core_get_db
    ] = override_get_db

    client = TestClient(app)

    try:
        yield client

    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(
            original_overrides
        )


def _create_second_customer(
    db_session: Session,
    source_customer: Customer,
) -> Customer:
    """
    Create a second customer in the same tenant by
    copying the source customer's persisted scalar fields.
    """
    mapper = sa_inspect(Customer)

    customer_data = {}

    for column in mapper.columns:
        if column.primary_key:
            continue

        if column.name == "tenant_id":
            continue

        if column.name in {
            "created_at",
            "updated_at",
        }:
            continue

        value = getattr(
            source_customer,
            column.name,
        )

        if value is not None and column.unique:
            if isinstance(value, str):
                value = (
                    f"{value}-"
                    f"{uuid4().hex[:8]}"
                )

        customer_data[column.name] = value

    customer_data["tenant_id"] = TENANT_ID

    second_customer = Customer(
        **customer_data
    )

    db_session.add(second_customer)
    db_session.flush()

    return second_customer


def _create_order_payload(
    order_number: str,
    customer_id: UUID,
    customer_address_id: UUID,
) -> dict:
    """
    Build a DELIVERY order payload.
    """
    return {
        "branch_id": str(BRANCH_ID),
        "customer_id": str(customer_id),
        "customer_address_id": str(
            customer_address_id
        ),
        "order_number": order_number,
        "order_type": "DELIVERY",
        "note": (
            "Customer address ownership integration test."
        ),
        "items": [
            {
                "product_variant_id": str(
                    PRODUCT_VARIANT_ID
                ),
                "quantity": 1,
            }
        ],
    }


def test_address_belonging_to_another_customer_is_rejected(
    authenticated_client,
    db_session: Session,
):
    """
    Verify that a customer cannot use an address
    belonging to another customer.
    """
    client = authenticated_client

    address = db_session.scalar(
        select(CustomerAddress).where(
            CustomerAddress.tenant_id == TENANT_ID
        )
    )

    assert address is not None

    source_customer = db_session.scalar(
        select(Customer).where(
            Customer.id == address.customer_id,
            Customer.tenant_id == TENANT_ID,
        )
    )

    assert source_customer is not None

    other_customer = _create_second_customer(
        db_session=db_session,
        source_customer=source_customer,
    )

    assert other_customer.id != source_customer.id
    assert other_customer.tenant_id == TENANT_ID

    order_number = (
        f"TEST-ADDRESS-MISMATCH-"
        f"{uuid4().hex[:8]}"
    )

    response = client.post(
        "/api/v1/orders",
        json=_create_order_payload(
            order_number=order_number,
            customer_id=other_customer.id,
            customer_address_id=address.id,
        ),
    )

    assert response.status_code == 404

    payload = response.json()

    assert (
        payload["detail"]
        == "Customer address not found."
    )

    list_response = client.get(
        "/api/v1/orders",
        params={
            "limit": 100,
            "offset": 0,
        },
    )

    assert list_response.status_code == 200

    orders = list_response.json()["items"]

    matching_orders = [
        order
        for order in orders
        if order["order_number"] == order_number
    ]

    assert matching_orders == []