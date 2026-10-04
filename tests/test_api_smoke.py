from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_openapi_endpoint_is_available():
    response = client.get("/openapi.json")

    assert response.status_code == 200

    data = response.json()

    assert "openapi" in data
    assert "paths" in data


def test_swagger_docs_are_available():
    response = client.get("/docs")

    assert response.status_code == 200
    assert "Swagger UI" in response.text


def test_redoc_is_available():
    response = client.get("/redoc")

    assert response.status_code == 200
    assert "ReDoc" in response.text


def test_main_api_routes_are_registered():
    response = client.get("/openapi.json")

    assert response.status_code == 200

    paths = response.json()["paths"]

    expected_paths = {
        "/api/v1/orders/sales-by-hour",
        "/api/v1/orders/sales-by-weekday",
        "/api/v1/orders/busy-hours",
        "/api/v1/orders/sales-by-weekday-hour",
        "/api/v1/orders/daily-business-summary",
        "/api/v1/orders/business-dashboard-summary",
        "/api/v1/orders/business-risk-metrics",
    }

    missing_paths = expected_paths - paths.keys()

    assert not missing_paths, (
        f"Expected API routes are missing from OpenAPI: {missing_paths}"
    )