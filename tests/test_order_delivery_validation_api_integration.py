"""
Integration tests for delivery order validation.
"""

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_data
from app.core.dependencies import get_db as core_get_db
from app.database.connection import get_db as connection_get_db
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


def _create_delivery_payload(
    order_number: str,
    customer_id=None,
    customer_address_id=None,
) -> dict:
    """
    Build a delivery order payload.
    """
    return {
        "branch_id": str(BRANCH_ID),
        "customer_id": customer_id,
        "customer_address_id": customer_address_id,
        "order_number": order_number,
        "order_type": "DELIVERY",
        "note": "Delivery validation integration test.",
        "items": [
            {
                "product_variant_id": str(
                    PRODUCT_VARIANT_ID
                ),
                "quantity": 1,
            }
        ],
    }


def test_delivery_order_requires_customer(
    authenticated_client,
):
    """
    Verify that a DELIVERY order cannot be created
    without a customer.
    """
    client = authenticated_client

    order_number = (
        f"TEST-DELIVERY-NO-CUSTOMER-"
        f"{uuid4().hex[:8]}"
    )

    response = client.post(
        "/api/v1/orders",
        json=_create_delivery_payload(
            order_number=order_number,
            customer_id=None,
            customer_address_id=None,
        ),
    )

    assert response.status_code == 400

    orders_response = client.get(
        "/api/v1/orders",
        params={
            "limit": 100,
            "offset": 0,
        },
    )

    assert orders_response.status_code == 200

    orders = orders_response.json()["items"]

    matching_orders = [
        order
        for order in orders
        if order["order_number"]
        == order_number
    ]

    assert matching_orders == []


def test_delivery_order_with_address_still_requires_customer(
    authenticated_client,
):
    """
    Verify that providing an address ID alone does not
    allow a DELIVERY order without a customer.
    """
    client = authenticated_client

    order_number = (
        f"TEST-DELIVERY-ADDRESS-NO-CUSTOMER-"
        f"{uuid4().hex[:8]}"
    )

    fake_address_id = str(uuid4())

    response = client.post(
        "/api/v1/orders",
        json=_create_delivery_payload(
            order_number=order_number,
            customer_id=None,
            customer_address_id=fake_address_id,
        ),
    )

    assert response.status_code == 400

    orders_response = client.get(
        "/api/v1/orders",
        params={
            "limit": 100,
            "offset": 0,
        },
    )

    assert orders_response.status_code == 200

    orders = orders_response.json()["items"]

    matching_orders = [
        order
        for order in orders
        if order["order_number"]
        == order_number
    ]

    assert matching_orders == []