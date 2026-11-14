"""NYC Open Data / Socrata public 311 ingestion, limited to a small recent slice."""
from datetime import datetime, timezone
import httpx
from sqlalchemy.orm import Session
from .models import Complaint

DATASET_ID = "erm2-nwe9"  # Official 311 Service Requests from 2020 to Present
API_URL = f"https://data.cityofnewyork.us/resource/{DATASET_ID}.json"
FIELDS = "unique_key,created_date,complaint_type,descriptor,borough,status,latitude,longitude"


def normalize(row: dict) -> dict | None:
    """Validate public rows and normalize to our internal schema."""
    try:
        key = str(row["unique_key"]).strip()
        created_at = datetime.fromisoformat(row["created_date"].replace("Z", "+00:00"))
        borough = str(row.get("borough") or "UNSPECIFIED").upper()
        kind = str(row.get("complaint_type") or "Unknown")
        status = str(row.get("status") or "Unknown")
        latitude = float(row["latitude"]) if row.get("latitude") is not None else None
        longitude = float(row["longitude"]) if row.get("longitude") is not None else None
        if not key or not (-90 <= latitude <= 90 if latitude is not None else True):
            return None
        if longitude is not None and not -180 <= longitude <= 180:
            return None
        return dict(source_id=key, source="nyc311", created_at=created_at.astimezone(timezone.utc).replace(tzinfo=None)
                    if created_at.tzinfo else created_at, complaint_type=kind, descriptor=str(row.get("descriptor") or ""),
                    borough=borough, status=status, latitude=latitude, longitude=longitude)
    except (KeyError, ValueError, TypeError):
        return None


async def fetch_recent(limit: int = 500) -> list[dict]:
    params = {"$select": FIELDS, "$order": "created_date DESC", "$limit": limit}
    async with httpx.AsyncClient(timeout=25, headers={"User-Agent": "CityOS educational prototype (GitHub project)"}) as client:
        response = await client.get(API_URL, params=params)
        response.raise_for_status()
        rows = response.json()
    if not isinstance(rows, list):
        raise ValueError("Unexpected NYC Open Data API response")
    return rows


def upsert_records(db: Session, records: list[dict]) -> tuple[int, int]:
    """Idempotent inserts. Returns accepted (normalized) and newly inserted row count."""
    from sqlalchemy import select
    accepted = [normalized for r in records if (normalized := normalize(r)) is not None]
    if not accepted:
        return 0, 0
    # Portable SQLAlchemy implementation (works on SQLite and Postgres).
    keys = [r["source_id"] for r in accepted]
    existing = set(db.scalars(select(Complaint.source_id).where(Complaint.source_id.in_(keys))).all())
    new = [Complaint(**r) for r in accepted if r["source_id"] not in existing]
    db.add_all(new)
    db.commit()
    return len(accepted), len(new)
