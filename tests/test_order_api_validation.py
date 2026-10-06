"""
API validation tests for the order listing endpoint.
"""

from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.core.auth import get_current_user_data
from app.main import app


client = TestClient(app)


TENANT_ID = UUID(
    "25291ef5-0240-4042-aabc-b92c5aa4957a"
)


@pytest.fixture
def authenticated_api():
    """
    Override authentication for API validation tests.
    """

    app.dependency_overrides[
        get_current_user_data
    ] = lambda: {
        "tenant_id": TENANT_ID,
    }

    yield

    app.dependency_overrides.pop(
        get_current_user_data,
        None,
    )


@pytest.mark.parametrize(
    "query",
    [
        "limit=0",
        "limit=-1",
        "limit=101",
        "offset=-1",
    ],
)
def test_orders_api_rejects_invalid_pagination(
    authenticated_api,
    query,
):
    response = client.get(
        f"/api/v1/orders?{query}"
    )

    assert response.status_code == 422


def test_orders_api_rejects_invalid_customer_id(
    authenticated_api,
):
    response = client.get(
        "/api/v1/orders?customer_id=not-a-uuid"
    )

    assert response.status_code == 422


def test_orders_api_rejects_invalid_branch_id(
    authenticated_api,
):
    response = client.get(
        "/api/v1/orders?branch_id=not-a-uuid"
    )

    assert response.status_code == 422


def test_orders_api_rejects_invalid_status(
    authenticated_api,
):
    response = client.get(
        "/api/v1/orders?status=INVALID_STATUS"
    )

    assert response.status_code == 422