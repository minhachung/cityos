"""Public deployment safety: anonymous viewers cannot trigger ingestion."""
from fastapi.testclient import TestClient
from app.main import app


def test_public_demo_disables_write_endpoint(monkeypatch):
    monkeypatch.setenv("CITYOS_PUBLIC_DEMO", "1")
    response = TestClient(app).post("/api/ingest")
    assert response.status_code == 403
    assert "disabled" in response.json()["detail"].lower()
