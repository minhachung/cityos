"""Single-owner admin access for the CityOS portfolio demo.

A password is stored ONLY as a salted PBKDF2 hash in the deployment environment.
Opaque random sessions are stored by digest in process memory. This fits a
single-instance prototype: sessions are intentionally lost on server restart.
"""
from __future__ import annotations

from collections import defaultdict, deque
import base64
import binascii
import hashlib
import hmac
import os
import secrets
import time
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

COOKIE_NAME = "cityos_admin"
SESSION_SECONDS = 4 * 60 * 60
ATTEMPT_WINDOW = 15 * 60
MAX_FAILED_ATTEMPTS = 5
MAX_SESSIONS = 16
ITERATIONS = 600_000

router = APIRouter(prefix="/api/admin", tags=["admin"])
_sessions: dict[str, float] = {}
_failed_logins: dict[str, deque[float]] = defaultdict(deque)


def _encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode(encoded: str) -> bytes:
    return base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))


def hash_password(password: str) -> str:
    """For the local setup script; never print/log the plaintext password."""
    if len(password) < 14:
        raise ValueError("Admin password must be at least 14 characters")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${_encode(salt)}${_encode(digest)}"


def configured() -> bool:
    encoded = os.getenv("CITYOS_ADMIN_PASSWORD_HASH", "")
    parts = encoded.split("$")
    if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
        return False
    try:
        iterations = int(parts[1])
        return iterations >= ITERATIONS and len(_decode(parts[2])) >= 16 and len(_decode(parts[3])) == 32
    except (ValueError, TypeError, OverflowError, binascii.Error):
        return False


def needs_admin() -> bool:
    return os.getenv("CITYOS_PUBLIC_DEMO") == "1" or configured()


def _verify_password(password: str) -> bool:
    if not configured():
        return False
    _, iterations, salt_b64, expected_b64 = os.environ["CITYOS_ADMIN_PASSWORD_HASH"].split("$")
    try:
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), _decode(salt_b64), int(iterations))
        return hmac.compare_digest(actual, _decode(expected_b64))
    except (ValueError, OverflowError, binascii.Error):
        return False


def _session_key(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def is_authenticated(request: Request) -> bool:
    if not configured():
        return False
    token = request.cookies.get(COOKIE_NAME, "")
    if not token or len(token) > 256:
        return False
    key = _session_key(token)
    expires = _sessions.get(key, 0)
    if expires <= time.time():
        _sessions.pop(key, None)
        return False
    return True


def require_same_origin_action(request: Request) -> None:
    # A non-simple header is required for all mutating admin requests; browsers
    # cannot send it cross-origin without a successful CORS preflight.
    if request.headers.get("x-cityos-request") != "1":
        raise HTTPException(status_code=403, detail="Missing admin request header")
    origin = request.headers.get("origin")
    if origin:
        parsed = urlsplit(origin)
        host = request.headers.get("host", "")
        if parsed.scheme not in ("http", "https") or parsed.netloc.lower() != host.lower():
            raise HTTPException(status_code=403, detail="Cross-origin admin requests are not permitted")


def require_admin(request: Request) -> None:
    if not configured():
        raise HTTPException(status_code=403, detail="Admin synchronization is disabled until configured")
    require_same_origin_action(request)
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Admin sign-in required")


class LoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=1024)


@router.get("/status")
def status(request: Request, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return {"enabled": configured(), "requires_auth": needs_admin(),
            "authenticated": is_authenticated(request)}


@router.post("/login")
def login(payload: LoginRequest, request: Request, response: Response):
    require_same_origin_action(request)
    response.headers["Cache-Control"] = "no-store"
    if not configured():
        raise HTTPException(status_code=503, detail="Admin sign-in is not configured")
    # In-memory failed-login limits protect the one-instance portfolio demo.
    # A production multi-instance service should use a shared rate limiter.
    client = request.client.host if request.client else "unknown"
    now = time.time()
    attempts = _failed_logins[client]
    while attempts and attempts[0] <= now - ATTEMPT_WINDOW:
        attempts.popleft()
    if len(attempts) >= MAX_FAILED_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Too many attempts. Try again later")
    if not _verify_password(payload.password):
        attempts.append(now)
        raise HTTPException(status_code=401, detail="Incorrect admin password")
    attempts.clear()
    # Bound the number of sessions and keep only digests in server memory.
    for key, expiry in list(_sessions.items()):
        if expiry <= now:
            _sessions.pop(key, None)
    if len(_sessions) >= MAX_SESSIONS:
        oldest = min(_sessions, key=_sessions.__getitem__)
        _sessions.pop(oldest)
    token = secrets.token_urlsafe(32)
    _sessions[_session_key(token)] = now + SESSION_SECONDS
    response.set_cookie(COOKIE_NAME, token, max_age=SESSION_SECONDS, path="/api",
                        secure=os.getenv("CITYOS_PUBLIC_DEMO") == "1", httponly=True, samesite="strict")
    return {"authenticated": True}


@router.post("/logout")
def logout(request: Request, response: Response):
    require_same_origin_action(request)
    response.headers["Cache-Control"] = "no-store"
    token = request.cookies.get(COOKIE_NAME)
    if token:
        _sessions.pop(_session_key(token), None)
    response.delete_cookie(COOKIE_NAME, path="/api", secure=os.getenv("CITYOS_PUBLIC_DEMO") == "1",
                           httponly=True, samesite="strict")
    return {"authenticated": False}
