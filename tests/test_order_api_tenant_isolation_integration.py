"""
Integration tests for Order API tenant isolation.
"""

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_data
from app.core.dependencies import get_db as core_get_db
from app.database.connection import get_db as connection_get_db
from app.main import app


TENANT_A_ID = UUID(
    "25291ef5-0240-4042-aabc-b92c5aa4957a"
)

TENANT_B_ID = UUID(
    "00000000-0000-0000-0000-000000000999"
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

    current_tenant_id = {
        "value": TENANT_A_ID
    }

    def override_current_user():
        return {
            "user_id": USER_ID,
            "tenant_id": current_tenant_id["value"],
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
        yield client, current_tenant_id

    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(
            original_overrides
        )


def test_order_api_rejects_cross_tenant_access(
    authenticated_client,
):
    """
    Verify that an order created by Tenant A cannot
    be accessed through Order APIs by Tenant B.
    """
    client, current_tenant_id = authenticated_client

    # ---------------------------------------------------------
    # 1. Create order while authenticated as Tenant A
    # ---------------------------------------------------------

    order_number = (
        f"TEST-TENANT-ISOLATION-"
        f"{uuid4().hex[:8]}"
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

    created_order = create_response.json()

    order_id = created_order["id"]

    assert (
        created_order["tenant_id"]
        == str(TENANT_A_ID)
    )
    assert (
        created_order["order_number"]
        == order_number
    )
    assert (
        created_order["status"]
        == "REGISTERED"
    )

    # Confirm Tenant A can access its own order.
    own_order_response = client.get(
        f"/api/v1/orders/{order_id}"
    )

    assert own_order_response.status_code == 200

    own_order = own_order_response.json()

    assert own_order["id"] == order_id
    assert (
        own_order["tenant_id"]
        == str(TENANT_A_ID)
    )

    # ---------------------------------------------------------
    # 2. Switch authentication context to Tenant B
    # ---------------------------------------------------------

    current_tenant_id["value"] = TENANT_B_ID

    # ---------------------------------------------------------
    # 3. Tenant B cannot read the order
    # ---------------------------------------------------------

    cross_tenant_order_response = client.get(
        f"/api/v1/orders/{order_id}"
    )

    assert (
        cross_tenant_order_response.status_code
        == 404
    )

    assert (
        cross_tenant_order_response.json()
        == {"detail": "Order not found."}
    )

    # ---------------------------------------------------------
    # 4. Tenant B cannot read status history
    # ---------------------------------------------------------

    cross_tenant_history_response = client.get(
        (
            f"/api/v1/orders/"
            f"{order_id}/status-history"
        )
    )

    assert (
        cross_tenant_history_response.status_code
        == 404
    )

    assert (
        cross_tenant_history_response.json()
        == {"detail": "Order not found."}
    )

    # ---------------------------------------------------------
    # 5. Tenant B cannot read ingredient requirements
    # ---------------------------------------------------------

    cross_tenant_requirements_response = client.get(
        (
            f"/api/v1/orders/"
            f"{order_id}/ingredient-requirements"
        )
    )

    assert (
        cross_tenant_requirements_response.status_code
        == 404
    )

    assert (
        cross_tenant_requirements_response.json()
        == {"detail": "Order not found."}
    )

    # ---------------------------------------------------------
    # 6. Tenant B cannot change the order status
    # ---------------------------------------------------------

    cross_tenant_status_response = client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={
            "status": "CANCELLED",
        },
    )

    assert (
        cross_tenant_status_response.status_code
        == 404
    )

    assert (
        cross_tenant_status_response.json()
        == {"detail": "Order not found."}
    )

    # ---------------------------------------------------------
    # 7. Tenant B cannot cancel the order
    # ---------------------------------------------------------

    cross_tenant_cancel_response = client.post(
        f"/api/v1/orders/{order_id}/cancel"
    )

    assert (
        cross_tenant_cancel_response.status_code
        == 404
    )

    assert (
        cross_tenant_cancel_response.json()
        == {"detail": "Order not found."}
    )

    # ---------------------------------------------------------
    # 8. Switch back to Tenant A and verify order is unchanged
    # ---------------------------------------------------------

    current_tenant_id["value"] = TENANT_A_ID

    final_response = client.get(
        f"/api/v1/orders/{order_id}"
    )

    assert final_response.status_code == 200

    final_order = final_response.json()

    assert final_order["id"] == order_id
    assert (
        final_order["tenant_id"]
        == str(TENANT_A_ID)
    )
    assert (
        final_order["status"]
        == "REGISTERED"
    )