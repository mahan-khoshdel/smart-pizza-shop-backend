"""
Integration tests for duplicate order number handling.
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


def _create_order_payload(
    order_number: str,
) -> dict:
    """
    Build a valid test order payload.
    """
    return {
        "branch_id": str(BRANCH_ID),
        "customer_id": None,
        "customer_address_id": None,
        "order_number": order_number,
        "order_type": "DINE_IN",
        "note": "Duplicate order number integration test.",
        "items": [
            {
                "product_variant_id": str(
                    PRODUCT_VARIANT_ID
                ),
                "quantity": 1,
            }
        ],
    }


def test_duplicate_order_number_is_rejected_by_api(
    authenticated_client,
):
    """
    Verify that the same order number cannot be used
    twice inside the same tenant.
    """
    client = authenticated_client

    # ---------------------------------------------------------
    # 1. Create the first order
    # ---------------------------------------------------------

    order_number = (
        f"TEST-DUPLICATE-{uuid4().hex[:8]}"
    )

    first_response = client.post(
        "/api/v1/orders",
        json=_create_order_payload(
            order_number
        ),
    )

    assert first_response.status_code == 201

    first_order = first_response.json()

    first_order_id = first_order["id"]

    assert (
        first_order["order_number"]
        == order_number
    )
    assert (
        first_order["tenant_id"]
        == str(TENANT_ID)
    )
    assert (
        first_order["status"]
        == "REGISTERED"
    )

    # ---------------------------------------------------------
    # 2. Try to create another order with
    #    the same order number
    # ---------------------------------------------------------

    duplicate_response = client.post(
        "/api/v1/orders",
        json=_create_order_payload(
            order_number
        ),
    )

    assert (
        duplicate_response.status_code
        == 409
    )

    duplicate_payload = (
        duplicate_response.json()
    )

    assert (
        duplicate_payload["detail"]
        == "Order number already exists."
    )

    # ---------------------------------------------------------
    # 3. Verify the original order still exists
    # ---------------------------------------------------------

    get_response = client.get(
        f"/api/v1/orders/{first_order_id}"
    )

    assert get_response.status_code == 200

    stored_order = get_response.json()

    assert (
        stored_order["id"]
        == first_order_id
    )
    assert (
        stored_order["order_number"]
        == order_number
    )
    assert (
        stored_order["tenant_id"]
        == str(TENANT_ID)
    )
    assert (
        stored_order["status"]
        == "REGISTERED"
    )

    # ---------------------------------------------------------
    # 4. Verify only the original order uses
    #    this exact order number
    # ---------------------------------------------------------

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
        if order["order_number"]
        == order_number
    ]

    assert len(matching_orders) == 1
    assert (
        matching_orders[0]["id"]
        == first_order_id
    )