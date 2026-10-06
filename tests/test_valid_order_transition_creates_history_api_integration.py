"""
Integration tests for valid order transition history creation.
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
            "Valid transition history integration test."
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


def test_valid_order_transition_creates_history(
    authenticated_client,
):
    """
    Verify that a valid status transition creates
    exactly one additional order status history record.
    """
    client = authenticated_client

    order_number = (
        f"TEST-VALID-HISTORY-"
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

    history_before_response = client.get(
        f"/api/v1/orders/{order_id}/status-history",
    )

    assert history_before_response.status_code == 200

    history_before = history_before_response.json()

    assert isinstance(history_before, list)
    assert len(history_before) == 1

    assert history_before[0]["order_id"] == order_id
    assert history_before[0]["from_status"] is None
    assert history_before[0]["to_status"] == "REGISTERED"

    transition_response = client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={
            "status": "PREPARING",
        },
    )

    assert transition_response.status_code == 200

    transitioned_order = transition_response.json()

    assert transitioned_order["status"] == "PREPARING"

    history_after_response = client.get(
        f"/api/v1/orders/{order_id}/status-history",
    )

    assert history_after_response.status_code == 200

    history_after = history_after_response.json()

    assert isinstance(history_after, list)
    assert len(history_after) == 2

    assert history_after[0]["order_id"] == order_id
    assert history_after[0]["from_status"] is None
    assert history_after[0]["to_status"] == "REGISTERED"

    assert history_after[1]["order_id"] == order_id
    assert history_after[1]["from_status"] == "REGISTERED"
    assert history_after[1]["to_status"] == "PREPARING"

    get_response = client.get(
        f"/api/v1/orders/{order_id}",
    )

    assert get_response.status_code == 200

    current_order = get_response.json()

    assert current_order["status"] == "PREPARING"