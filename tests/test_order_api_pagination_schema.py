"""
OpenAPI contract tests for the paginated order response.
"""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _get_orders_operation(openapi: dict) -> dict:
    """
    Return the GET /orders operation from the OpenAPI document.
    """

    for path, operations in openapi["paths"].items():
        if path.endswith("/orders") and "get" in operations:
            return operations["get"]

    raise AssertionError(
        "GET /orders endpoint was not found in OpenAPI."
    )


def _get_pagination_schema(openapi: dict) -> dict:
    """
    Return the OrderPaginationResponse schema.
    """

    schemas = openapi["components"]["schemas"]

    assert "OrderPaginationResponse" in schemas

    return schemas["OrderPaginationResponse"]


def test_order_pagination_response_has_required_fields():
    response = client.get("/openapi.json")

    assert response.status_code == 200

    openapi = response.json()
    schema = _get_pagination_schema(openapi)

    assert set(schema["required"]) == {
        "items",
        "total",
        "limit",
        "offset",
    }


def test_order_pagination_response_defines_items_as_array():
    response = client.get("/openapi.json")

    assert response.status_code == 200

    openapi = response.json()
    schema = _get_pagination_schema(openapi)

    items_schema = schema["properties"]["items"]

    assert items_schema["type"] == "array"


def test_order_pagination_items_reference_order_response():
    response = client.get("/openapi.json")

    assert response.status_code == 200

    openapi = response.json()
    schema = _get_pagination_schema(openapi)

    items_schema = schema["properties"]["items"]

    assert items_schema["items"]["$ref"].endswith(
        "/OrderResponse"
    )


def test_order_pagination_metadata_types_are_correct():
    response = client.get("/openapi.json")

    assert response.status_code == 200

    openapi = response.json()
    schema = _get_pagination_schema(openapi)

    properties = schema["properties"]

    assert properties["total"]["type"] == "integer"
    assert properties["limit"]["type"] == "integer"
    assert properties["offset"]["type"] == "integer"


def test_orders_get_operation_uses_pagination_response():
    response = client.get("/openapi.json")

    assert response.status_code == 200

    openapi = response.json()
    operation = _get_orders_operation(openapi)

    response_schema = operation["responses"]["200"][
        "content"
    ]["application/json"]["schema"]

    assert response_schema["$ref"].endswith(
        "/OrderPaginationResponse"
    )