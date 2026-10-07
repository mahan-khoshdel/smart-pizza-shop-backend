"""
Integration tests for missing required fields
in the order status update API.
"""

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_data
from app.core.dependencies import get_db as core_get_db
from app.database.connection import get_db as connection_get_db
from app.main import app
from app.schemas.order import OrderCreate
from app.services.order import create_order


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


def test_order_status_update_requires_status_field(
    authenticated_client,
    db_session: Session,
):
    """
    Verify that the order status update API rejects
    a request body without the required status field.
    """
    client = authenticated_client

    order_number = (
        f"TEST-MISSING-STATUS-{uuid4().hex[:8]}"
    )

    order_data = OrderCreate(
        branch_id=BRANCH_ID,
        customer_id=None,
        customer_address_id=None,
        order_number=order_number,
        order_type="DINE_IN",
        note="Missing status field test.",
        items=[
            {
                "product_variant_id": PRODUCT_VARIANT_ID,
                "quantity": 1,
            }
        ],
    )

    created_order = create_order(
        db=db_session,
        tenant_id=TENANT_ID,
        data=order_data,
    )

    order_id = created_order["id"]

    assert created_order["status"] == "REGISTERED"

    response = client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={},
    )

    assert response.status_code == 422

    payload = response.json()

    assert "detail" in payload
    assert payload["detail"]

    verify_response = client.get(
        f"/api/v1/orders/{order_id}",
    )

    assert verify_response.status_code == 200

    verify_payload = verify_response.json()

    assert verify_payload["status"] == "REGISTERED"
    assert verify_payload["inventory_consumed_at"] is None