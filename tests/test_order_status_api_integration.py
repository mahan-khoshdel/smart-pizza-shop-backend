"""
Integration tests for the Order Status API.
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


def _create_test_order(
    client: TestClient,
) -> dict:
    """
    Create a real test order through the API.
    """
    payload = {
        "branch_id": str(BRANCH_ID),
        "customer_id": None,
        "customer_address_id": None,
        "order_number": (
            f"TEST-STATUS-{uuid4().hex[:8]}"
        ),
        "order_type": "DINE_IN",
        "note": "Order status API integration test.",
        "items": [
            {
                "product_variant_id": str(
                    PRODUCT_VARIANT_ID
                ),
                "quantity": 1,
            }
        ],
    }

    response = client.post(
        "/api/v1/orders",
        json=payload,
    )

    assert response.status_code == 201

    return response.json()


def test_order_status_api_updates_status_and_rejects_invalid_transition(
    authenticated_client,
):
    """
    Verify the Order Status API through a real HTTP lifecycle:

    CREATE
        ->
    REGISTERED
        ->
    CANCELLED
        ->
    INVALID CANCELLED -> PREPARING
        ->
    VERIFY ORDER
        ->
    VERIFY STATUS HISTORY
    """
    client = authenticated_client

    # ---------------------------------------------------------
    # 1. Create order
    # ---------------------------------------------------------

    created_order = _create_test_order(client)

    order_id = created_order["id"]

    assert created_order["status"] == "REGISTERED"
    assert (
        created_order["inventory_consumed_at"]
        is None
    )

    # ---------------------------------------------------------
    # 2. REGISTERED -> CANCELLED through status API
    # ---------------------------------------------------------

    cancel_status_response = client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={
            "status": "CANCELLED",
        },
    )

    assert (
        cancel_status_response.status_code
        == 200
    )

    cancelled_order = (
        cancel_status_response.json()
    )

    assert cancelled_order["id"] == order_id
    assert (
        cancelled_order["status"]
        == "CANCELLED"
    )
    assert (
        cancelled_order["inventory_consumed_at"]
        is None
    )

    # ---------------------------------------------------------
    # 3. CANCELLED -> PREPARING must be rejected
    # ---------------------------------------------------------

    invalid_transition_response = client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={
            "status": "PREPARING",
        },
    )

    assert (
        invalid_transition_response.status_code
        == 400
    )

    invalid_detail = (
        invalid_transition_response.json()
    )

    assert (
        invalid_detail["detail"]
        == (
            "Invalid status transition: "
            "CANCELLED -> PREPARING."
        )
    )

    # ---------------------------------------------------------
    # 4. Verify invalid transition did not change order
    # ---------------------------------------------------------

    get_order_response = client.get(
        f"/api/v1/orders/{order_id}"
    )

    assert get_order_response.status_code == 200

    current_order = get_order_response.json()

    assert current_order["id"] == order_id
    assert (
        current_order["status"]
        == "CANCELLED"
    )
    assert (
        current_order["inventory_consumed_at"]
        is None
    )

    # ---------------------------------------------------------
    # 5. Verify status history
    # ---------------------------------------------------------

    history_response = client.get(
        (
            f"/api/v1/orders/"
            f"{order_id}/status-history"
        )
    )

    assert history_response.status_code == 200

    history = history_response.json()

    assert len(history) == 2

    assert history[0]["order_id"] == order_id
    assert (
        history[0]["from_status"]
        is None
    )
    assert (
        history[0]["to_status"]
        == "REGISTERED"
    )

    assert history[1]["order_id"] == order_id
    assert (
        history[1]["from_status"]
        == "REGISTERED"
    )
    assert (
        history[1]["to_status"]
        == "CANCELLED"
    )

    assert (
        history[0]["changed_at"]
        <= history[1]["changed_at"]
    )