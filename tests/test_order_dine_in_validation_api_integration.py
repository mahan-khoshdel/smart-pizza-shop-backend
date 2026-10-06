"""
Integration tests for DINE_IN order validation.
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


def _create_dine_in_payload(
    order_number: str,
) -> dict:
    """
    Build a valid DINE_IN order payload
    without customer information.
    """
    return {
        "branch_id": str(BRANCH_ID),
        "customer_id": None,
        "customer_address_id": None,
        "order_number": order_number,
        "order_type": "DINE_IN",
        "note": "DINE_IN validation integration test.",
        "items": [
            {
                "product_variant_id": str(
                    PRODUCT_VARIANT_ID
                ),
                "quantity": 1,
            }
        ],
    }


def test_dine_in_order_can_be_created_without_customer(
    authenticated_client,
):
    """
    Verify that a DINE_IN order does not require
    a customer or delivery address.
    """
    client = authenticated_client

    order_number = (
        f"TEST-DINE-IN-NO-CUSTOMER-"
        f"{uuid4().hex[:8]}"
    )

    response = client.post(
        "/api/v1/orders",
        json=_create_dine_in_payload(
            order_number
        ),
    )

    assert response.status_code == 201

    order = response.json()

    assert order["order_number"] == order_number
    assert order["tenant_id"] == str(TENANT_ID)
    assert order["branch_id"] == str(BRANCH_ID)
    assert order["order_type"] == "DINE_IN"
    assert order["status"] == "REGISTERED"
    assert order["customer_id"] is None

    order_id = order["id"]

    get_response = client.get(
        f"/api/v1/orders/{order_id}"
    )

    assert get_response.status_code == 200

    stored_order = get_response.json()

    assert stored_order["id"] == order_id
    assert stored_order["order_number"] == order_number
    assert stored_order["order_type"] == "DINE_IN"
    assert stored_order["customer_id"] is None


def test_dine_in_order_does_not_require_delivery_address(
    authenticated_client,
):
    """
    Verify that a DINE_IN order can be created without
    any delivery address information.
    """
    client = authenticated_client

    order_number = (
        f"TEST-DINE-IN-NO-ADDRESS-"
        f"{uuid4().hex[:8]}"
    )

    response = client.post(
        "/api/v1/orders",
        json=_create_dine_in_payload(
            order_number
        ),
    )

    assert response.status_code == 201

    order = response.json()

    assert order["order_type"] == "DINE_IN"
    assert order["customer_id"] is None

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
        item
        for item in orders
        if item["order_number"] == order_number
    ]

    assert len(matching_orders) == 1
    assert matching_orders[0]["order_type"] == "DINE_IN"
    assert matching_orders[0]["customer_id"] is None