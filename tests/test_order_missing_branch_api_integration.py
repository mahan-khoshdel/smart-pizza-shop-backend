"""
Integration tests for missing branch validation.
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
    branch_id: UUID,
) -> dict:
    """
    Build an order payload using the supplied branch ID.
    """
    return {
        "branch_id": str(branch_id),
        "customer_id": None,
        "customer_address_id": None,
        "order_number": order_number,
        "order_type": "DINE_IN",
        "note": "Missing branch integration test.",
        "items": [
            {
                "product_variant_id": str(
                    PRODUCT_VARIANT_ID
                ),
                "quantity": 1,
            }
        ],
    }


def test_missing_branch_is_rejected(
    authenticated_client,
):
    """
    Verify that an order cannot be created when
    its branch does not exist for the current tenant.
    """
    client = authenticated_client

    missing_branch_id = uuid4()

    order_number = (
        f"TEST-MISSING-BRANCH-"
        f"{uuid4().hex[:8]}"
    )

    response = client.post(
        "/api/v1/orders",
        json=_create_order_payload(
            order_number=order_number,
            branch_id=missing_branch_id,
        ),
    )

    assert response.status_code == 404

    payload = response.json()

    assert (
        payload["detail"]
        == "Branch not found."
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
        if order["order_number"]
        == order_number
    ]

    assert matching_orders == []