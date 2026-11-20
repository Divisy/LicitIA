"""Tests for tenders API endpoints."""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_list_tenders_empty():
    """Test that /api/v1/tenders returns 200 and empty list when DB has no tenders."""
    response = client.get("/api/v1/tenders")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert isinstance(data["items"], list)
    assert data["total"] == 0


