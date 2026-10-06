from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _find_kitchen_performance_paths(openapi: dict) -> list[str]:
    paths = openapi["paths"]

    return [
        path
        for path in paths
        if "kitchen" in path.lower()
        and "performance" in path.lower()
    ]


def test_kitchen_performance_api_route_is_registered():
    """
    Verify that the Kitchen Performance API route
    is registered in OpenAPI.
    """

    response = client.get("/openapi.json")

    assert response.status_code == 200

    openapi = response.json()

    matching_paths = _find_kitchen_performance_paths(
        openapi
    )

    assert matching_paths, (
        "No Kitchen Performance API route "
        "was found in OpenAPI."
    )


def test_kitchen_performance_api_requires_authentication():
    """
    Verify that the Kitchen Performance endpoint
    is protected by the authentication layer.
    """

    response = client.get("/openapi.json")

    assert response.status_code == 200

    openapi = response.json()

    matching_paths = _find_kitchen_performance_paths(
        openapi
    )

    assert matching_paths, (
        "No Kitchen Performance API route "
        "was found in OpenAPI."
    )

    for path in matching_paths:
        operations = openapi["paths"][path]

        assert "get" in operations

        get_operation = operations["get"]

        assert (
            get_operation.get("security")
            or openapi.get("security")
        )