"""
API tests for order pagination and filtering metadata.
"""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _get_orders_operation(openapi: dict) -> dict:
    """
    Return the GET /orders operation from OpenAPI.

    The exact path may include the API version prefix.
    """

    for path, operations in openapi["paths"].items():
        if path.endswith("/orders"):
            if "get" in operations:
                return operations["get"]

    raise AssertionError(
        "GET /orders endpoint was not found in OpenAPI."
    )


def test_orders_api_declares_pagination_response():
    """
    Verify that the Order List API uses the pagination response schema.
    """

    response = client.get("/openapi.json")

    assert response.status_code == 200

    openapi = response.json()

    operation = _get_orders_operation(openapi)

    schema = operation["responses"]["200"]["content"][
        "application/json"
    ]["schema"]

    assert schema["$ref"].endswith(
        "/OrderPaginationResponse"
    )


def test_orders_api_declares_pagination_parameters():
    """
    Verify that pagination and filtering query parameters
    are exposed through OpenAPI.
    """

    response = client.get("/openapi.json")

    assert response.status_code == 200

    openapi = response.json()

    operation = _get_orders_operation(openapi)

    parameters = {
        parameter["name"]
        for parameter in operation.get(
            "parameters",
            [],
        )
    }

    assert "status" in parameters
    assert "customer_id" in parameters
    assert "branch_id" in parameters
    assert "limit" in parameters
    assert "offset" in parameters


def test_orders_api_pagination_limits_are_documented():
    """
    Verify that limit and offset expose their validation
    constraints through OpenAPI.
    """

    response = client.get("/openapi.json")

    assert response.status_code == 200

    openapi = response.json()

    operation = _get_orders_operation(openapi)

    parameters = {
        parameter["name"]: parameter
        for parameter in operation.get(
            "parameters",
            [],
        )
    }

    limit_schema = parameters["limit"]["schema"]
    offset_schema = parameters["offset"]["schema"]

    assert limit_schema["minimum"] == 1
    assert limit_schema["maximum"] == 100
    assert offset_schema["minimum"] == 0


def test_orders_api_requires_authentication():
    """
    Verify that the Order List API remains protected.
    """

    response = client.get(
        "/api/v1/orders"
    )

    assert response.status_code in {
        401,
        403,
    }