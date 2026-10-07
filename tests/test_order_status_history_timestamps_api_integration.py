"""
Integration tests for order status history timestamps.
"""

from datetime import datetime
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
            "Status history timestamp integration test."
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


def test_order_status_history_has_valid_chronological_timestamps(
    authenticated_client,
):
    """
    Verify that order status history contains valid
    chronological changed_at timestamps.
    """
    client = authenticated_client

    order_number = (
        f"TEST-HISTORY-TIMESTAMPS-"
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

    preparing_response = client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={
            "status": "PREPARING",
        },
    )

    assert preparing_response.status_code == 200

    ready_response = client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={
            "status": "READY",
        },
    )

    assert ready_response.status_code == 200

    history_response = client.get(
        f"/api/v1/orders/{order_id}/status-history",
    )

    assert history_response.status_code == 200

    history = history_response.json()

    assert isinstance(history, list)
    assert len(history) == 3

    assert history[0]["from_status"] is None
    assert history[0]["to_status"] == "REGISTERED"

    assert history[1]["from_status"] == "REGISTERED"
    assert history[1]["to_status"] == "PREPARING"

    assert history[2]["from_status"] == "PREPARING"
    assert history[2]["to_status"] == "READY"

    timestamps = []

    for entry in history:
        assert entry["order_id"] == order_id
        assert entry["changed_at"] is not None

        timestamp = datetime.fromisoformat(
            entry["changed_at"].replace(
                "Z",
                "+00:00",
            )
        )

        timestamps.append(timestamp)

    assert timestamps[0] <= timestamps[1]
    assert timestamps[1] <= timestamps[2]