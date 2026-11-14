"""CityOS backend: filter and aggregate service requests; sync official 311 records."""
from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Annotated
import httpx
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from .db import Base, engine, get_db, SessionLocal
from .models import Complaint
from .sample import seed_demo
from .ingest import fetch_recent, upsert_records
from .priority import priority_for
from .allocation import allocate


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if db.scalar(select(func.count()).select_from(Complaint)) == 0:
            seed_demo(db)
    # The public portfolio demo refreshes a bounded public-data snapshot on boot.
    # On Render's free tier SQLite is ephemeral; this is intentional, not persistence.
    if os.getenv("CITYOS_PUBLIC_DEMO") == "1":
        try:
            rows = await fetch_recent(500)
            with SessionLocal() as db:
                upsert_records(db, rows)
        except (httpx.HTTPError, ValueError, OSError) as exc:
            logging.getLogger(__name__).warning("NYC 311 startup import failed: %s", exc)
    yield


app = FastAPI(title="CityOS API", version="0.3.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
Db = Annotated[Session, Depends(get_db)]


class ComplaintOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    source_id: str
    source: str
    created_at: datetime
    complaint_type: str
    descriptor: str
    borough: str
    status: str
    latitude: float | None
    longitude: float | None


class Page(BaseModel):
    items: list[ComplaintOut]
    total: int
    page: int
    page_size: int


@app.get("/health")
def health():
    return {"status": "ok", "application": "cityos"}


def build_filters(borough: str | None, status: str | None, q: str | None):
    filters = []
    if borough and borough.upper() != "ALL":
        filters.append(Complaint.borough == borough.upper())
    if status and status.upper() != "ALL":
        filters.append(func.lower(Complaint.status) == status.lower())
    if q and q.strip():
        term = f"%{q.strip()}%"
        filters.append(or_(Complaint.complaint_type.ilike(term), Complaint.descriptor.ilike(term)))
    return filters


@app.get("/api/complaints", response_model=Page)
def get_complaints(db: Db, borough: str | None = None, status: str | None = None,
                   q: str | None = None, page: int = Query(1, ge=1),
                   page_size: int = Query(100, ge=1, le=500)):
    filters = build_filters(borough, status, q)
    total = db.scalar(select(func.count()).select_from(Complaint).where(*filters)) or 0
    items = db.scalars(select(Complaint).where(*filters).order_by(Complaint.created_at.desc())
                       .offset((page - 1) * page_size).limit(page_size)).all()
    return Page(items=items, total=total, page=page, page_size=page_size)


@app.get("/api/stats")
def get_stats(db: Db, borough: str | None = None, status: str | None = None, q: str | None = None):
    filters = build_filters(borough, status, q)
    total = db.scalar(select(func.count()).select_from(Complaint).where(*filters)) or 0
    demo = db.scalar(select(func.count()).select_from(Complaint).where(*filters, Complaint.source == "demo")) or 0
    status_rows = db.execute(select(Complaint.status, func.count()).where(*filters)
                             .group_by(Complaint.status)).all()
    category_rows = db.execute(select(Complaint.complaint_type, func.count()).where(*filters)
                               .group_by(Complaint.complaint_type).order_by(func.count().desc()).limit(6)).all()
    borough_rows = db.execute(select(Complaint.borough, func.count()).where(*filters)
                              .group_by(Complaint.borough).order_by(func.count().desc())).all()
    open_count = sum(n for name, n in status_rows if str(name).lower() not in ("closed", "resolved"))
    return {"total": total, "open": open_count, "closed": total - open_count, "demo": demo,
            "by_category": [{"label": name, "count": count} for name, count in category_rows],
            "by_borough": [{"label": name, "count": count} for name, count in borough_rows]}


class PriorityOut(ComplaintOut):
    score: int
    band: str
    age_days: int
    age_points: int
    category_points: int
    category_rule: str
    explanation: str


class PriorityPage(BaseModel):
    items: list[PriorityOut]
    total: int
    as_of: str
    methodology: str


PRIORITY_NOTICE = (
    "Experimental review-order heuristic. Weights are student-defined, not NYC policy "
    "or verified severity assessments; never use for real dispatch or emergencies."
)


@app.get("/api/priorities", response_model=PriorityPage)
def get_priorities(db: Db, borough: str | None = None, q: str | None = None,
                   include_demo: bool = False, limit: int = Query(10, ge=1, le=50)):
    """Rank ALL matching unresolved stored requests before limiting the response.

    This in-memory algorithm is appropriate for the bounded educational dataset;
    a production version would score/filter via SQL and paginate at scale.
    """
    filters = build_filters(borough, None, q)
    filters.append(func.lower(Complaint.status).not_in(("closed", "resolved")))
    if not include_demo:
        filters.append(Complaint.source == "nyc311")
    as_of = datetime.now(timezone.utc).date()
    complaints = db.scalars(select(Complaint).where(*filters)).all()
    ranked = [priority_for(complaint, as_of) for complaint in complaints]
    ranked.sort(key=lambda item: (-item["score"], item["created_at"], item["source_id"]))
    return PriorityPage(items=ranked[:limit], total=len(ranked), as_of=as_of.isoformat(),
                        methodology=PRIORITY_NOTICE)


@app.get("/api/allocation")
def get_allocation(db: Db, borough: str | None = None, q: str | None = None,
                   include_demo: bool = False,
                   crew_count: int = Query(8, ge=1, le=8),
                   candidate_limit: int = Query(60, ge=1, le=150)):
    """Simulate one assignment per fictional crew, compared with FIFO."""
    filters = build_filters(borough, None, q)
    filters.append(func.lower(Complaint.status).not_in(("closed", "resolved")))
    if not include_demo:
        filters.append(Complaint.source == "nyc311")
    rows = db.scalars(select(Complaint).where(*filters)).all()
    return allocate(rows, datetime.now(timezone.utc).date(), crew_count, candidate_limit)


@app.post("/api/ingest")
async def ingest(db: Db, limit: int = Query(500, ge=1, le=1000)):
    if os.getenv("CITYOS_PUBLIC_DEMO") == "1":
        raise HTTPException(status_code=403, detail="Public demo is read-only; data refreshes on service startup.")
    try:
        rows = await fetch_recent(limit)
        accepted, inserted = upsert_records(db, rows)
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=f"NYC Open Data is unavailable: {exc}") from exc
    return {"fetched": len(rows), "accepted": accepted, "inserted": inserted,
            "message": "Imported official NYC 311 records. Demo records remain clearly labeled."}


# Docker production build copies the Vite output here. Keep this AFTER API routes
# so /api/*, /health, and /docs continue to resolve to FastAPI.
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="dashboard")
