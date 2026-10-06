"""Tests for health check endpoint."""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    """Test that health endpoint returns 200 and correct status."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_allows_production_frontend_preflight():
    origin = "https://licitia-frontend-production.up.railway.app"
    response = client.options(
        "/api/v1/auth/request-code",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code in (200, 204)
    assert response.headers.get("access-control-allow-origin") == origin

