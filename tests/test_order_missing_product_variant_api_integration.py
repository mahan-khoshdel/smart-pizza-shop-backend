"""
Integration tests for missing product variant validation.
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
    product_variant_id: UUID,
) -> dict:
    """
    Build an order payload using the supplied
    product variant ID.
    """
    return {
        "branch_id": str(BRANCH_ID),
        "customer_id": None,
        "customer_address_id": None,
        "order_number": order_number,
        "order_type": "DINE_IN",
        "note": "Missing product variant integration test.",
        "items": [
            {
                "product_variant_id": str(
                    product_variant_id
                ),
                "quantity": 1,
            }
        ],
    }


def test_missing_product_variant_is_rejected(
    authenticated_client,
):
    """
    Verify that an order cannot be created when
    its product variant does not exist.
    """
    client = authenticated_client

    missing_product_variant_id = uuid4()

    order_number = (
        f"TEST-MISSING-VARIANT-"
        f"{uuid4().hex[:8]}"
    )

    response = client.post(
        "/api/v1/orders",
        json=_create_order_payload(
            order_number=order_number,
            product_variant_id=missing_product_variant_id,
        ),
    )

    assert response.status_code == 404

    payload = response.json()

    assert (
        payload["detail"]
        == (
            "Product variant not found: "
            f"{missing_product_variant_id}"
        )
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