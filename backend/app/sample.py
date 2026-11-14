"""Fictional NYC-looking records for offline demos. NEVER represent as NYC 311 data."""
from datetime import datetime, timedelta, timezone
from .models import Complaint

# All coordinates are illustrative geographic points, not real 311 complaints.
SAMPLE = [
    ("BROOKLYN", "Street Condition", "Pothole", "Open", 40.6782, -73.9442),
    ("MANHATTAN", "Noise - Residential", "Loud Music/Party", "Open", 40.7512, -73.9851),
    ("QUEENS", "Illegal Parking", "Blocked Driveway", "Open", 40.7282, -73.7949),
    ("BRONX", "Street Light Condition", "Street Light Out", "In Progress", 40.8448, -73.8648),
    ("STATEN ISLAND", "Sanitation Condition", "Overflowing Litter Basket", "Closed", 40.5795, -74.1502),
    ("BROOKLYN", "Water System", "Water Leak", "Open", 40.6458, -73.9521),
    ("MANHATTAN", "Street Condition", "Pothole", "In Progress", 40.7851, -73.9712),
    ("QUEENS", "Noise - Residential", "Loud Talking", "Closed", 40.7421, -73.8825),
    ("BRONX", "Illegal Parking", "Double Parked Blocking Traffic", "Open", 40.8176, -73.9170),
    ("BROOKLYN", "Dirty Conditions", "Trash", "Closed", 40.6929, -73.9904),
    ("MANHATTAN", "Noise - Commercial", "Loud Music", "Open", 40.7155, -74.0033),
    ("QUEENS", "Street Condition", "Pothole", "Open", 40.7533, -73.9196),
    ("STATEN ISLAND", "Street Light Condition", "Street Light Out", "In Progress", 40.6157, -74.0845),
    ("BRONX", "Water System", "Hydrant Leaking", "Closed", 40.8539, -73.9008),
    ("BROOKLYN", "Illegal Parking", "Commercial Vehicle", "Open", 40.7076, -73.9570),
    ("MANHATTAN", "Dirty Conditions", "Garbage", "Closed", 40.7652, -73.9799),
    ("QUEENS", "Sanitation Condition", "Overflowing Litter Basket", "Open", 40.7044, -73.7992),
    ("BROOKLYN", "Noise - Residential", "Loud Television", "In Progress", 40.6713, -73.9777),
]


def seed_demo(db):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    entries = [
        Complaint(
            source_id=f"DEMO-{i:04}", source="demo",
            created_at=now - timedelta(hours=(i * 7 + 2)), complaint_type=t,
            descriptor=d, status=s, borough=b, latitude=lat, longitude=lon,
        )
        for i, (b, t, d, s, lat, lon) in enumerate(SAMPLE, 1)
    ]
    db.add_all(entries)
    db.commit()
