"""
Integration tests for order API filters and pagination.
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


def _create_order(
    client: TestClient,
    *,
    order_number: str,
    customer_id: str | None = None,
) -> dict:
    """
    Create a test order through the real API.
    """
    payload = {
        "branch_id": str(BRANCH_ID),
        "customer_id": customer_id,
        "customer_address_id": None,
        "order_number": order_number,
        "order_type": "DINE_IN",
        "note": "Order API filter integration test.",
        "items": [
            {
                "product_variant_id": str(
                    PRODUCT_VARIANT_ID
                ),
                "quantity": 1,
            }
        ],
    }

    response = client.post(
        "/api/v1/orders",
        json=payload,
    )

    assert response.status_code == 201

    return response.json()


def test_order_api_filters_and_pagination(
    authenticated_client,
):
    """
    Verify that the real Order API correctly combines:

    - customer filtering
    - status filtering
    - branch filtering
    - limit/offset pagination
    """
    client = authenticated_client

    # ---------------------------------------------------------
    # 1. Create a unique customer
    # ---------------------------------------------------------

    suffix = uuid4().hex[:9]

    customer_payload = {
        "first_name": "Filter",
        "last_name": f"Customer-{suffix}",
        "phone": f"09{suffix}",
        "email": (
            f"filter-{suffix}"
            "@example.com"
        ),
        "notes": "Order filter integration test customer.",
    }

    customer_response = client.post(
        "/api/v1/customers",
        json=customer_payload,
    )

    assert customer_response.status_code == 200

    customer = customer_response.json()
    customer_id = customer["id"]

    # ---------------------------------------------------------
    # 2. Create two orders for the same customer
    # ---------------------------------------------------------

    first_order = _create_order(
        client,
        order_number=(
            f"TEST-FILTER-A-{uuid4().hex[:8]}"
        ),
        customer_id=customer_id,
    )

    second_order = _create_order(
        client,
        order_number=(
            f"TEST-FILTER-B-{uuid4().hex[:8]}"
        ),
        customer_id=customer_id,
    )

    first_order_id = first_order["id"]
    second_order_id = second_order["id"]

    assert first_order["status"] == "REGISTERED"
    assert second_order["status"] == "REGISTERED"

    # ---------------------------------------------------------
    # 3. Cancel the second order
    # ---------------------------------------------------------

    cancel_response = client.post(
        f"/api/v1/orders/{second_order_id}/cancel"
    )

    assert cancel_response.status_code == 200

    cancelled_order = cancel_response.json()

    assert cancelled_order["id"] == second_order_id
    assert cancelled_order["status"] == "CANCELLED"

    # ---------------------------------------------------------
    # 4. Filter by customer
    # ---------------------------------------------------------

    customer_filter_response = client.get(
        "/api/v1/orders",
        params={
            "customer_id": customer_id,
        },
    )

    assert customer_filter_response.status_code == 200

    customer_result = (
        customer_filter_response.json()
    )

    assert customer_result["total"] == 2
    assert customer_result["limit"] == 20
    assert customer_result["offset"] == 0
    assert len(customer_result["items"]) == 2

    customer_order_ids = {
        item["id"]
        for item in customer_result["items"]
    }

    assert customer_order_ids == {
        first_order_id,
        second_order_id,
    }

    for item in customer_result["items"]:
        assert item["customer_id"] == customer_id

    # ---------------------------------------------------------
    # 5. Customer filter + pagination: first page
    # ---------------------------------------------------------

    first_page_response = client.get(
        "/api/v1/orders",
        params={
            "customer_id": customer_id,
            "limit": 1,
            "offset": 0,
        },
    )

    assert first_page_response.status_code == 200

    first_page = first_page_response.json()

    assert first_page["total"] == 2
    assert first_page["limit"] == 1
    assert first_page["offset"] == 0
    assert len(first_page["items"]) == 1

    first_page_order_id = (
        first_page["items"][0]["id"]
    )

    # ---------------------------------------------------------
    # 6. Customer filter + pagination: second page
    # ---------------------------------------------------------

    second_page_response = client.get(
        "/api/v1/orders",
        params={
            "customer_id": customer_id,
            "limit": 1,
            "offset": 1,
        },
    )

    assert second_page_response.status_code == 200

    second_page = second_page_response.json()

    assert second_page["total"] == 2
    assert second_page["limit"] == 1
    assert second_page["offset"] == 1
    assert len(second_page["items"]) == 1

    second_page_order_id = (
        second_page["items"][0]["id"]
    )

    assert first_page_order_id != second_page_order_id

    assert {
        first_page_order_id,
        second_page_order_id,
    } == {
        first_order_id,
        second_order_id,
    }

    # ---------------------------------------------------------
    # 7. Filter by status
    # ---------------------------------------------------------

    cancelled_response = client.get(
        "/api/v1/orders",
        params={
            "status": "CANCELLED",
        },
    )

    assert cancelled_response.status_code == 200

    cancelled_result = (
        cancelled_response.json()
    )

    assert cancelled_result["total"] >= 1

    cancelled_ids = {
        item["id"]
        for item in cancelled_result["items"]
    }

    assert second_order_id in cancelled_ids

    for item in cancelled_result["items"]:
        assert item["status"] == "CANCELLED"

    # ---------------------------------------------------------
    # 8. Combine status filter with pagination
    # ---------------------------------------------------------

    cancelled_page_response = client.get(
        "/api/v1/orders",
        params={
            "status": "CANCELLED",
            "limit": 1,
            "offset": 0,
        },
    )

    assert cancelled_page_response.status_code == 200

    cancelled_page = (
        cancelled_page_response.json()
    )

    assert cancelled_page["total"] >= 1
    assert cancelled_page["limit"] == 1
    assert cancelled_page["offset"] == 0
    assert len(cancelled_page["items"]) == 1
    assert (
        cancelled_page["items"][0]["status"]
        == "CANCELLED"
    )

    # ---------------------------------------------------------
    # 9. Filter by branch
    # ---------------------------------------------------------

    branch_response = client.get(
        "/api/v1/orders",
        params={
            "branch_id": str(BRANCH_ID),
            "customer_id": customer_id,
        },
    )

    assert branch_response.status_code == 200

    branch_result = branch_response.json()

    assert branch_result["total"] == 2

    for item in branch_result["items"]:
        assert item["branch_id"] == str(BRANCH_ID)
        assert item["customer_id"] == customer_id