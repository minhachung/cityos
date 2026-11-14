"""Run with `pytest -q` from backend/; no network access required."""
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db import Base, get_db
from app.main import app
from app.models import Complaint
from app.ingest import normalize, upsert_records

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(bind=engine, expire_on_commit=False)
Base.metadata.create_all(bind=engine)


def override_db():
    with TestingSession() as db:
        yield db


app.dependency_overrides[get_db] = override_db


def setup_function():
    with TestingSession() as db:
        db.query(Complaint).delete()
        db.add_all([
            Complaint(source_id="1", source="demo", created_at=datetime(2026, 11, 5),
                      complaint_type="Pothole", descriptor="Road", borough="BROOKLYN", status="Open",
                      latitude=40.7, longitude=-73.9),
            Complaint(source_id="2", source="nyc311", created_at=datetime(2026, 11, 6),
                      complaint_type="Noise", descriptor="Loud Music", borough="QUEENS", status="Closed",
                      latitude=40.7, longitude=-73.8),
        ])
        db.commit()


def test_health():
    assert TestClient(app).get("/health").json()["status"] == "ok"


def test_list_filters():
    with TestClient(app) as c:
        assert c.get("/api/complaints").json()["total"] == 2
        r = c.get("/api/complaints", params={"borough": "brooklyn", "status": "open"}).json()
        assert r["total"] == 1 and r["items"][0]["source_id"] == "1"
        assert c.get("/api/complaints", params={"q": "LOUD"}).json()["total"] == 1


def test_stats_and_pagination():
    with TestClient(app) as c:
        r = c.get("/api/stats").json()
        assert (r["total"], r["open"], r["closed"], r["demo"]) == (2, 1, 1, 1)
        assert len(c.get("/api/complaints", params={"page_size": 1}).json()["items"]) == 1
        assert c.get("/api/complaints", params={"page_size": 1000}).status_code == 422


def test_normalization_and_idempotent_import():
    valid = {"unique_key": "abc", "created_date": "2026-11-09T12:00:00.000", "complaint_type": "Water",
             "borough": "brooklyn", "status": "Open", "latitude": "40.6", "longitude": "-73.7"}
    assert normalize(valid)["borough"] == "BROOKLYN"
    assert normalize({"unique_key": "bad"}) is None
    with TestingSession() as db:
        assert upsert_records(db, [valid]) == (1, 1)
        assert upsert_records(db, [valid]) == (1, 0)
        assert db.scalar(select(Complaint.source).where(Complaint.source_id == "abc")) == "nyc311"


def test_ingest_endpoint_with_mocked_nyc_api(monkeypatch):
    from app import main

    async def fake_fetch_recent(limit):
        assert limit == 2
        return [{"unique_key": "311-123", "created_date": "2026-11-12T13:00:00.000", "complaint_type": "Pothole",
                 "descriptor": "Road defect", "borough": "Brooklyn", "status": "Open",
                 "latitude": "40.69", "longitude": "-73.96"}]

    monkeypatch.setattr(main, "fetch_recent", fake_fetch_recent)
    with TestClient(app) as c:
        result = c.post("/api/ingest?limit=2")
        assert result.status_code == 200
        assert result.json()["inserted"] == 1
        again = c.post("/api/ingest?limit=2")
        assert again.json()["inserted"] == 0
        assert c.get("/api/complaints", params={"q": "road defect"}).json()["total"] == 1


def test_invalid_coordinates_rejected():
    assert normalize({"unique_key": "bad", "created_date": "2026-11-12T00:00:00",
                      "latitude": "400", "longitude": "-73"}) is None
