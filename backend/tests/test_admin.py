"""Single-owner admin authentication and write-endpoint security."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import _failed_logins, _sessions, hash_password, is_authenticated
from app.db import Base, get_db
from app.main import app

PASSWORD = "fairly-long-demo-test-password"
ORIGIN = "https://testserver"
HEADERS = {"X-CityOS-Request": "1", "Origin": ORIGIN}


@pytest.fixture(autouse=True)
def auth_setup(monkeypatch):
    # Keep tests independent of the live NYC 311 API even when lifespan runs.
    from app import main
    async def offline_fetch_recent(limit):
        return []
    monkeypatch.setattr(main, "fetch_recent", offline_fetch_recent)
    _failed_logins.clear()
    _sessions.clear()
    monkeypatch.setenv("CITYOS_PUBLIC_DEMO", "1")
    monkeypatch.setenv("CITYOS_ADMIN_PASSWORD_HASH", hash_password(PASSWORD))
    yield
    _failed_logins.clear()
    _sessions.clear()


def client():
    return TestClient(app, base_url=ORIGIN)


def test_unauthenticated_visitor_still_can_read_but_cannot_sync():
    with client() as c:
        assert c.get("/api/admin/status").json() == {"enabled": True, "requires_auth": True, "authenticated": False}
        assert c.get("/api/stats").status_code == 200
        assert c.post("/api/ingest", headers=HEADERS).status_code == 401
        assert c.post("/api/ingest").status_code == 403


def test_login_allows_sync_and_logout_revokes_access(monkeypatch):
    from app import main
    async def fake_fetch_recent(limit):
        return [{"unique_key": "123456", "created_date": "2026-11-11T10:00:00.000",
                 "complaint_type": "Noise", "borough": "Queens", "status": "Open"}]
    monkeypatch.setattr(main, "fetch_recent", fake_fetch_recent)
    # Use an isolated DB; the public demo DB should not be modified by tests.
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    def override_db():
        with Session() as db:
            yield db
    old = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_db
    try:
        with client() as c:
            invalid = c.post("/api/admin/login", headers=HEADERS, json={"password": "invalid"})
            assert invalid.status_code == 401
            signed = c.post("/api/admin/login", headers=HEADERS, json={"password": PASSWORD})
            assert signed.status_code == 200
            assert "httponly" in signed.headers["set-cookie"].lower()
            assert "secure" in signed.headers["set-cookie"].lower()
            assert "samesite=strict" in signed.headers["set-cookie"].lower()
            assert c.get("/api/admin/status").json()["authenticated"] is True
            sync = c.post("/api/ingest?limit=1", headers=HEADERS)
            assert sync.status_code == 200 and sync.json()["inserted"] == 1
            assert c.post("/api/ingest?limit=1", headers={"X-CityOS-Request": "1", "Origin": "https://evil.example"}).status_code == 403
            assert c.post("/api/admin/logout", headers=HEADERS).status_code == 200
            assert c.get("/api/admin/status").json()["authenticated"] is False
            assert c.post("/api/ingest?limit=1", headers=HEADERS).status_code == 401
    finally:
        if old is not None:
            app.dependency_overrides[get_db] = old
        else:
            app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def test_login_requires_csrf_header_and_correct_origin():
    with client() as c:
        assert c.post("/api/admin/login", json={"password": PASSWORD}).status_code == 403
        assert c.post("/api/admin/login", headers={**HEADERS, "Origin": "https://evil.example"},
                      json={"password": PASSWORD}).status_code == 403
        assert c.get("/api/admin/status").json()["authenticated"] is False


def test_login_throttles_wrong_guesses():
    with client() as c:
        for _ in range(5):
            assert c.post("/api/admin/login", headers=HEADERS, json={"password": "nope"}).status_code == 401
        assert c.post("/api/admin/login", headers=HEADERS, json={"password": PASSWORD}).status_code == 429


def test_session_expires(monkeypatch):
    import app.auth as auth
    with client() as c:
        assert c.post("/api/admin/login", headers=HEADERS, json={"password": PASSWORD}).status_code == 200
        assert c.get("/api/admin/status").json()["authenticated"] is True
        now = auth.time.time()
        monkeypatch.setattr(auth.time, "time", lambda: now + auth.SESSION_SECONDS + 1)
        assert c.get("/api/admin/status").json()["authenticated"] is False
        assert c.post("/api/ingest", headers=HEADERS).status_code == 401


def test_missing_admin_config_fails_closed(monkeypatch):
    monkeypatch.delenv("CITYOS_ADMIN_PASSWORD_HASH")
    with client() as c:
        assert c.get("/api/admin/status").json() == {"enabled": False, "requires_auth": True, "authenticated": False}
        assert c.post("/api/ingest", headers=HEADERS).status_code == 403
        assert c.post("/api/admin/login", headers=HEADERS, json={"password": PASSWORD}).status_code == 503


def test_password_hash_randomized_and_requires_length():
    assert hash_password(PASSWORD) != hash_password(PASSWORD)
    with pytest.raises(ValueError):
        hash_password("too-short")
