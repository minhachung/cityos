"""Deterministic checks of the illustrative rule engine and priority API."""
from datetime import date, datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import Complaint
from app.priority import priority_for


def complaint(key, kind, created_at, *, status="Open", source="nyc311", borough="BROOKLYN"):
    return Complaint(source_id=key, source=source, created_at=created_at,
                     complaint_type=kind, descriptor="Test", borough=borough,
                     status=status, latitude=40.7, longitude=-73.9)


def test_explicit_weight_and_age_breakdown():
    score = priority_for(complaint("a", "Water System", datetime(2026, 11, 10)), date(2026, 11, 14))
    assert (score["category_points"], score["age_days"], score["age_points"], score["score"]) == (60, 4, 20, 80)
    assert score["band"] == "high"
    assert "Water system" in score["explanation"]


def test_age_cap_and_future_dates():
    old = priority_for(complaint("a", "Noise - Residential", datetime(2020, 1, 1)), date(2026, 11, 14))
    assert old["age_points"] == 40
    assert old["score"] == 60
    future = priority_for(complaint("b", "Other", datetime(2026, 11, 15)), date(2026, 11, 14))
    assert (future["age_days"], future["age_points"], future["score"]) == (0, 0, 25)


def test_unknown_categories_are_documented_default():
    result = priority_for(complaint("z", "Surprise category", datetime(2026, 11, 14)), date(2026, 11, 14))
    assert result["category_rule"] == "Other / unspecified"
    assert result["category_points"] == 25


def test_rankings_filters_demo_exclusion_and_closed_exclusion():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestingSession = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    with TestingSession() as db:
        db.add_all([
            complaint("noise", "Noise - Residential", datetime(2026, 11, 11)),
            complaint("water", "Water System", datetime(2026, 11, 10)),
            complaint("old", "Street Condition", datetime(2020, 11, 10), borough="QUEENS"),
            complaint("closed", "Water System", datetime(2020, 11, 10), status="Closed"),
            complaint("resolved", "Water System", datetime(2020, 11, 10), status="Resolved"),
            complaint("demo", "Water System", datetime(2020, 11, 10), source="demo"),
        ])
        db.commit()

    def override():
        with TestingSession() as db:
            yield db

    saved = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override
    try:
        with TestClient(app) as client:
            response = client.get("/api/priorities", params={"limit": 1})
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 3  # limit only applies after global ranking
            assert data["items"][0]["source_id"] == "old"
            assert "not NYC policy" in data["methodology"]
            all_rows = client.get("/api/priorities", params={"limit": 10}).json()["items"]
            assert [item["source_id"] for item in all_rows] == ["old", "water", "noise"]
            assert all(item["source"] == "nyc311" for item in all_rows)
            brooklyn = client.get("/api/priorities", params={"borough": "brooklyn", "q": "water"}).json()
            assert brooklyn["total"] == 1
            assert brooklyn["items"][0]["source_id"] == "water"
            with_demo = client.get("/api/priorities", params={"include_demo": "true"}).json()
            assert with_demo["total"] == 4
            assert any(item["source_id"] == "demo" for item in with_demo["items"])
            assert client.get("/api/priorities", params={"limit": 0}).status_code == 422
            assert client.get("/api/priorities", params={"limit": 51}).status_code == 422
    finally:
        if saved is None:
            del app.dependency_overrides[get_db]
        else:
            app.dependency_overrides[get_db] = saved
        engine.dispose()
