from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _find_product_paths(openapi: dict) -> list[str]:
    paths = openapi["paths"]

    return [
        path
        for path in paths
        if "product" in path.lower()
        and "order" not in path.lower()
        and "inventory" not in path.lower()
    ]


def test_product_api_routes_are_registered():
    response = client.get("/openapi.json")

    assert response.status_code == 200

    openapi = response.json()

    matching_paths = _find_product_paths(openapi)

    assert matching_paths, (
        "No Product API route "
        "was found in OpenAPI."
    )


def test_product_api_requires_authentication():
    response = client.get("/openapi.json")

    assert response.status_code == 200

    openapi = response.json()

    matching_paths = _find_product_paths(openapi)

    assert matching_paths, (
        "No Product API route "
        "was found in OpenAPI."
    )

    protected_operation_found = False

    for path in matching_paths:
        operations = openapi["paths"][path]

        for method in [
            "get",
            "post",
            "put",
            "patch",
            "delete",
        ]:
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
        "No protected Product API operation "
        "was found in OpenAPI."
    )