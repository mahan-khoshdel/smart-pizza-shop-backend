"""
Integration tests for tenant isolation during order status updates.
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

OTHER_TENANT_ID = uuid4()

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


def test_other_tenant_cannot_update_order_status(
    authenticated_client,
    db_session: Session,
):
    """
    Verify that another tenant cannot update the status
    of an order belonging to the current tenant.
    """
    client = authenticated_client

    order_number = (
        f"TEST-TENANT-STATUS-{uuid4().hex[:8]}"
    )

    order_data = OrderCreate(
        branch_id=BRANCH_ID,
        customer_id=None,
        customer_address_id=None,
        order_number=order_number,
        order_type="DINE_IN",
        note="Tenant isolation integration test.",
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

    def override_other_tenant():
        return {
            "user_id": USER_ID,
            "tenant_id": OTHER_TENANT_ID,
        }

    app.dependency_overrides[
        get_current_user_data
    ] = override_other_tenant

    response = client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={
            "status": "PREPARING",
        },
    )

    assert response.status_code == 404

    payload = response.json()

    assert payload["detail"] == "Order not found."

    def override_original_tenant():
        return {
            "user_id": USER_ID,
            "tenant_id": TENANT_ID,
        }

    app.dependency_overrides[
        get_current_user_data
    ] = override_original_tenant

    verify_response = client.get(
        f"/api/v1/orders/{order_id}",
    )

    assert verify_response.status_code == 200

    verify_payload = verify_response.json()

    assert verify_payload["id"] == str(order_id)
    assert verify_payload["status"] == "REGISTERED"