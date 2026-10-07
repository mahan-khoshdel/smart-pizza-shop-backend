"""
Integration tests for order kitchen capacity validation.
"""

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_data
from app.core.dependencies import get_db as core_get_db
from app.database.connection import get_db as connection_get_db
from app.database.models.branch import Branch
from app.main import app
from app.repositories.order import OrderRepository


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
            "Kitchen capacity validation integration test."
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


def test_order_cannot_start_preparing_when_kitchen_is_full(
    authenticated_client,
    db_session: Session,
):
    """
    Verify that an order cannot move to PREPARING when
    the branch kitchen has reached its capacity.
    """
    client = authenticated_client

    branch = db_session.scalar(
        select(Branch).where(
            Branch.id == BRANCH_ID,
            Branch.tenant_id == TENANT_ID,
        )
    )

    assert branch is not None

    original_kitchen_capacity = (
        branch.kitchen_capacity
    )

    try:
        order_number = (
            f"TEST-KITCHEN-CAPACITY-"
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

        repository = OrderRepository(db_session)

        workload = repository.get_kitchen_workload(
            tenant_id=TENANT_ID,
            branch_id=BRANCH_ID,
        )

        preparing_count = workload["preparing_count"]

        branch.kitchen_capacity = preparing_count

        db_session.flush()

        preparing_response = client.patch(
            f"/api/v1/orders/{order_id}/status",
            json={
                "status": "PREPARING",
            },
        )

        assert preparing_response.status_code == 409

        payload = preparing_response.json()

        assert payload["detail"] == (
            "Kitchen capacity reached. "
            f"Preparing orders: {preparing_count}. "
            f"Kitchen capacity: {preparing_count}."
        )

        get_response = client.get(
            f"/api/v1/orders/{order_id}",
        )

        assert get_response.status_code == 200

        current_order = get_response.json()

        assert current_order["status"] == "REGISTERED"

    finally:
        branch.kitchen_capacity = (
            original_kitchen_capacity
        )
        db_session.flush()