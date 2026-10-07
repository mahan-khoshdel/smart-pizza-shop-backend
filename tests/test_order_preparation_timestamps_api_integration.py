"""
Integration tests for order preparation timestamps.
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
from app.database.models.order import Order
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
            "Order preparation timestamps integration test."
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


def test_order_preparation_timestamps_are_recorded(
    authenticated_client,
    db_session: Session,
):
    """
    Verify that PREPARING and READY transitions record
    preparing_at and ready_at correctly.
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
        repository = OrderRepository(db_session)

        workload = repository.get_kitchen_workload(
            tenant_id=TENANT_ID,
            branch_id=BRANCH_ID,
        )

        preparing_count = workload["preparing_count"]

        if branch.kitchen_capacity <= preparing_count:
            branch.kitchen_capacity = (
                preparing_count + 1
            )
            db_session.flush()

        order_number = (
            f"TEST-TIMESTAMPS-"
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
        order_id = UUID(order["id"])

        assert order["status"] == "REGISTERED"

        db_order = db_session.scalar(
            select(Order).where(
                Order.id == order_id,
                Order.tenant_id == TENANT_ID,
            )
        )

        assert db_order is not None
        assert db_order.preparing_at is None
        assert db_order.ready_at is None

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

        db_order = db_session.scalar(
            select(Order).where(
                Order.id == order_id,
                Order.tenant_id == TENANT_ID,
            )
        )

        assert db_order is not None
        assert db_order.preparing_at is not None
        assert db_order.ready_at is None

        preparing_at = db_order.preparing_at

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

        db_order = db_session.scalar(
            select(Order).where(
                Order.id == order_id,
                Order.tenant_id == TENANT_ID,
            )
        )

        assert db_order is not None
        assert db_order.preparing_at is not None
        assert db_order.ready_at is not None

        assert db_order.preparing_at == preparing_at
        assert db_order.ready_at >= db_order.preparing_at

    finally:
        branch.kitchen_capacity = (
            original_kitchen_capacity
        )
        db_session.flush()