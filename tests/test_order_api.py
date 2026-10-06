from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _find_order_paths(openapi: dict) -> list[str]:
    paths = openapi["paths"]

    return [
        path
        for path in paths
        if "order" in path.lower()
        and "kitchen" not in path.lower()
        and "customer" not in path.lower()
        and "address" not in path.lower()
    ]


def test_order_api_route_is_registered():
    """
    Verify that the main Order API route
    is registered in OpenAPI.
    """

    response = client.get("/openapi.json")

    assert response.status_code == 200

    openapi = response.json()

    matching_paths = _find_order_paths(openapi)

    assert matching_paths, (
        "No main Order API route "
        "was found in OpenAPI."
    )


def test_order_api_requires_authentication():
    """
    Verify that the main Order API endpoint
    is protected by the authentication layer.
    """

    response = client.get("/openapi.json")

    assert response.status_code == 200

    openapi = response.json()

    matching_paths = _find_order_paths(openapi)

    assert matching_paths, (
        "No main Order API route "
        "was found in OpenAPI."
    )

    protected_operation_found = False

    for path in matching_paths:
        operations = openapi["paths"][path]

        for method in ["get", "post", "put", "patch", "delete"]:
            if method not in operations:
                continue

            operation = operations[method]

            if (
                operation.get("security")
                or openapi.get("security")
            ):
                protected_operation_found = True
                break

        if protected_operation_found:
            break

    assert protected_operation_found, (
        "No protected main Order API operation "
        "was found in OpenAPI."
    )