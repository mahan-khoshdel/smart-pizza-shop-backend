"""
Integration tests for unavailable product variant validation.
"""

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_data
from app.core.dependencies import get_db as core_get_db
from app.database.connection import get_db as connection_get_db
from app.database.models.product_variant import ProductVariant
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
    Build a valid order payload using the test product variant.
    """
    return {
        "branch_id": str(BRANCH_ID),
        "customer_id": None,
        "customer_address_id": None,
        "order_number": order_number,
        "order_type": "DINE_IN",
        "note": (
            "Unavailable product variant "
            "integration test."
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


def test_unavailable_product_variant_is_rejected(
    authenticated_client,
    db_session: Session,
):
    """
    Verify that an unavailable product variant cannot
    be added to a new order.
    """
    client = authenticated_client

    product_variant = db_session.scalar(
        select(ProductVariant).where(
            ProductVariant.id == PRODUCT_VARIANT_ID,
            ProductVariant.tenant_id == TENANT_ID,
        )
    )

    assert product_variant is not None
    assert product_variant.is_available is True

    order_number = (
        f"TEST-UNAVAILABLE-VARIANT-"
        f"{uuid4().hex[:8]}"
    )

    original_availability = (
        product_variant.is_available
    )

    try:
        product_variant.is_available = False
        db_session.flush()

        response = client.post(
            "/api/v1/orders",
            json=_create_order_payload(
                order_number
            ),
        )

        assert response.status_code == 400

        payload = response.json()

        assert (
            payload["detail"]
            == (
                "Product variant is not available: "
                f"{PRODUCT_VARIANT_ID}"
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

    finally:
        product_variant.is_available = (
            original_availability
        )
        db_session.flush()