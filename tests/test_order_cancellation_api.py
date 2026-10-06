from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _find_order_cancellation_operations(
    openapi: dict,
) -> list[tuple[str, str]]:
    operations = []

    for path, path_operations in openapi["paths"].items():
        path_lower = path.lower()

        if "order" not in path_lower:
            continue

        if "cancel" not in path_lower:
            continue

        for method in [
            "get",
            "post",
            "put",
            "patch",
            "delete",
        ]:
            if method in path_operations:
                operations.append((path, method))

    return operations


def test_order_cancellation_api_route_is_registered():
    """
    Verify that the Order Cancellation API operation
    is registered in OpenAPI.
    """

    response = client.get("/openapi.json")

    assert response.status_code == 200

    openapi = response.json()

    matching_operations = (
        _find_order_cancellation_operations(openapi)
    )

    assert matching_operations, (
        "No Order Cancellation API operation "
        "was found in OpenAPI."
    )


def test_order_cancellation_api_requires_authentication():
    """
    Verify that the Order Cancellation API operation
    is protected by the authentication layer.
    """

    response = client.get("/openapi.json")

    assert response.status_code == 200

    openapi = response.json()

    matching_operations = (
        _find_order_cancellation_operations(openapi)
    )

    assert matching_operations, (
        "No Order Cancellation API operation "
        "was found in OpenAPI."
    )

    for path, method in matching_operations:
        operation = openapi["paths"][path][method]

        assert (
            operation.get("security")
            or openapi.get("security")
        ), (
            "Order Cancellation API operation is not "
            "protected by the authentication layer: "
            f"{method.upper()} {path}"
        )