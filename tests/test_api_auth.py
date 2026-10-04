from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


PROTECTED_ENDPOINTS = [
    "/api/v1/orders/sales-by-hour",
    "/api/v1/orders/business-risk-metrics",
]


def test_protected_api_rejects_unauthenticated_request():
    for endpoint in PROTECTED_ENDPOINTS:
        response = client.get(endpoint)

        assert response.status_code in {401, 403}, (
            f"Expected authentication failure for {endpoint}, "
            f"but received HTTP {response.status_code}: {response.text}"
        )


def test_protected_api_declares_authentication_requirement():
    openapi_response = client.get("/openapi.json")

    assert openapi_response.status_code == 200

    openapi = openapi_response.json()
    paths = openapi["paths"]

    for endpoint in PROTECTED_ENDPOINTS:
        assert endpoint in paths, f"Endpoint is missing from OpenAPI: {endpoint}"

        operation = paths[endpoint]["get"]

        operation_security = operation.get("security")
        global_security = openapi.get("security")

        assert operation_security or global_security, (
            f"Endpoint does not declare an authentication requirement: {endpoint}"
        )