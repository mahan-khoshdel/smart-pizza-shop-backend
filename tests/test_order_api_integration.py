"""
Integration tests for the complete order API lifecycle.
"""

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_data
from app.database.connection import get_db
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
        get_db
    ] = override_get_db

    client = TestClient(app)

    try:
        yield client

    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(
            original_overrides
        )


def test_order_api_complete_lifecycle(
    authenticated_client,
):
    """
    Verify the complete API lifecycle:

    CREATE
        ->
    REGISTERED
        ->
    CANCELLED
        ->
    GET ORDER
        ->
    GET STATUS HISTORY
    """
    client = authenticated_client

    order_number = (
        f"TEST-E2E-{uuid4().hex[:8]}"
    )

    create_payload = {
        "branch_id": str(BRANCH_ID),
        "customer_id": None,
        "customer_address_id": None,
        "order_number": order_number,
        "order_type": "DINE_IN",
        "note": "End-to-end API integration test.",
        "items": [
            {
                "product_variant_id": str(
                    PRODUCT_VARIANT_ID
                ),
                "quantity": 1,
            }
        ],
    }

    # ---------------------------------------------------------
    # 1. Create order
    # ---------------------------------------------------------

    create_response = client.post(
        "/api/v1/orders",
        json=create_payload,
    )

    assert create_response.status_code == 201

    created_order = create_response.json()

    order_id = created_order["id"]

    assert created_order["tenant_id"] == str(
        TENANT_ID
    )
    assert created_order["branch_id"] == str(
        BRANCH_ID
    )
    assert (
        created_order["order_number"]
        == order_number
    )
    assert created_order["status"] == "REGISTERED"

    # ---------------------------------------------------------
    # 2. Cancel order
    # ---------------------------------------------------------

    cancel_response = client.post(
        f"/api/v1/orders/{order_id}/cancel"
    )

    assert cancel_response.status_code == 200

    cancelled_order = cancel_response.json()

    assert cancelled_order["id"] == order_id
    assert cancelled_order["tenant_id"] == str(
        TENANT_ID
    )
    assert cancelled_order["status"] == "CANCELLED"

    # Inventory must not be consumed by cancellation.
    assert (
        cancelled_order["inventory_consumed_at"]
        is None
    )

    # ---------------------------------------------------------
    # 3. Read the order through the API
    # ---------------------------------------------------------

    get_response = client.get(
        f"/api/v1/orders/{order_id}"
    )

    assert get_response.status_code == 200

    fetched_order = get_response.json()

    assert fetched_order["id"] == order_id
    assert fetched_order["tenant_id"] == str(
        TENANT_ID
    )
    assert (
        fetched_order["order_number"]
        == order_number
    )
    assert fetched_order["status"] == "CANCELLED"

    # ---------------------------------------------------------
    # 4. Read status history through the API
    # ---------------------------------------------------------

    history_response = client.get(
        f"/api/v1/orders/{order_id}/status-history"
    )

    assert history_response.status_code == 200

    history = history_response.json()

    assert len(history) == 2

    # Initial order state
    assert history[0]["order_id"] == order_id
    assert history[0]["from_status"] is None
    assert history[0]["to_status"] == "REGISTERED"
    assert history[0]["changed_at"] is not None

    # Cancellation state
    assert history[1]["order_id"] == order_id
    assert history[1]["from_status"] == "REGISTERED"
    assert history[1]["to_status"] == "CANCELLED"
    assert history[1]["changed_at"] is not None

    # The API must return the history in chronological order.
    assert history[0]["changed_at"] <= history[1][
        "changed_at"
    ]


def test_order_api_lifecycle_keeps_order_inside_current_tenant(
    authenticated_client,
):
    """
    Verify that the created order remains associated with
    the authenticated tenant throughout the API lifecycle.
    """
    client = authenticated_client

    order_number = (
        f"TEST-E2E-TENANT-{uuid4().hex[:8]}"
    )

    create_payload = {
        "branch_id": str(BRANCH_ID),
        "customer_id": None,
        "customer_address_id": None,
        "order_number": order_number,
        "order_type": "DINE_IN",
        "note": "Tenant isolation integration test.",
        "items": [
            {
                "product_variant_id": str(
                    PRODUCT_VARIANT_ID
                ),
                "quantity": 1,
            }
        ],
    }

    create_response = client.post(
        "/api/v1/orders",
        json=create_payload,
    )

    assert create_response.status_code == 201

    order_id = create_response.json()["id"]

    get_response = client.get(
        f"/api/v1/orders/{order_id}"
    )

    assert get_response.status_code == 200

    payload = get_response.json()

    assert payload["tenant_id"] == str(
        TENANT_ID
    )