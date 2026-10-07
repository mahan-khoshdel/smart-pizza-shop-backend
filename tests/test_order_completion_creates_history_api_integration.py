"""
Integration tests for order completion history creation.
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
    Build a valid DINE_IN order payload.
    """
    return {
        "branch_id": str(BRANCH_ID),
        "customer_id": None,
        "customer_address_id": None,
        "order_number": order_number,
        "order_type": "DINE_IN",
        "note": (
            "Order completion history integration test."
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


def test_order_completion_creates_history(
    authenticated_client,
):
    """
    Verify that completing an order creates the expected
    final status history record and consumes inventory.
    """
    client = authenticated_client

    order_number = (
        f"TEST-COMPLETE-HISTORY-"
        f"{uuid4().hex[:8]}"
    )

    create_response = client.post(
        "/api/v1/orders",
        json=_create_order_payload(
            order_number=order_number,
        ),
    )

    assert create_response.status_code == 201

    order = create_response.json()
    order_id = order["id"]

    assert order["status"] == "REGISTERED"
    assert order["inventory_consumed_at"] is None

    preparing_response = client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={
            "status": "PREPARING",
        },
    )

    assert preparing_response.status_code == 200
    assert (
        preparing_response.json()["status"]
        == "PREPARING"
    )

    ready_response = client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={
            "status": "READY",
        },
    )

    assert ready_response.status_code == 200
    assert (
        ready_response.json()["status"]
        == "READY"
    )

    completed_response = client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={
            "status": "COMPLETED",
        },
    )

    assert completed_response.status_code == 200

    completed_order = completed_response.json()

    assert completed_order["status"] == "COMPLETED"
    assert (
        completed_order["inventory_consumed_at"]
        is not None
    )

    history_response = client.get(
        f"/api/v1/orders/{order_id}/status-history",
    )

    assert history_response.status_code == 200

    history = history_response.json()

    assert isinstance(history, list)
    assert len(history) == 4

    assert history[0]["order_id"] == order_id
    assert history[0]["from_status"] is None
    assert history[0]["to_status"] == "REGISTERED"

    assert history[1]["order_id"] == order_id
    assert history[1]["from_status"] == "REGISTERED"
    assert history[1]["to_status"] == "PREPARING"

    assert history[2]["order_id"] == order_id
    assert history[2]["from_status"] == "PREPARING"
    assert history[2]["to_status"] == "READY"

    assert history[3]["order_id"] == order_id
    assert history[3]["from_status"] == "READY"
    assert history[3]["to_status"] == "COMPLETED"

    get_response = client.get(
        f"/api/v1/orders/{order_id}",
    )

    assert get_response.status_code == 200

    current_order = get_response.json()

    assert current_order["status"] == "COMPLETED"
    assert (
        current_order["inventory_consumed_at"]
        is not None
    )