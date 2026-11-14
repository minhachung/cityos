"""Transparent, illustrative NYC 311 review-order heuristic.

These weights are student-defined, NOT NYC policy or emergency-triage advice.
Do not interpret the score as actual harm, safety severity, or dispatch order.
"""
from datetime import date
from .models import Complaint

# Explicit broad category labels, not a trained risk classifier.
# The fallback deliberately avoids making severity claims about unknown categories.
CATEGORY_RULES = (
    ("water system", 60, "Water system"),
    ("sewer", 55, "Sewer"),
    ("street light condition", 50, "Street lighting"),
    ("street condition", 45, "Street condition"),
    ("sanitation condition", 35, "Sanitation"),
    ("illegal parking", 30, "Parking"),
    ("noise", 20, "Noise"),
)
DEFAULT_CATEGORY_POINTS = 25
MAX_AGE_POINTS = 40
POINTS_PER_DAY = 5


def priority_for(complaint: Complaint, as_of: date) -> dict:
    """Return explainable scoring components for a single unresolved complaint.

    Day-level age is used to avoid timezone precision claims: NYC's feed can
    contain local, timezone-naive timestamps. Dates in the future receive zero.
    """
    kind = complaint.complaint_type.strip().lower()
    rule_name, category_points = "Other / unspecified", DEFAULT_CATEGORY_POINTS
    for prefix, weight, label in CATEGORY_RULES:
        if kind.startswith(prefix):
            rule_name, category_points = label, weight
            break

    age_days = max(0, (as_of - complaint.created_at.date()).days)
    age_points = min(MAX_AGE_POINTS, age_days * POINTS_PER_DAY)
    score = min(100, category_points + age_points)
    band = "high" if score >= 70 else "medium" if score >= 45 else "low"
    explanation = (
        f"Prototype category rule: {rule_name} (+{category_points}); "
        f"reported {age_days} day{'s' if age_days != 1 else ''} ago "
        f"(+{age_points}, capped at {MAX_AGE_POINTS})."
    )
    return {
        "source_id": complaint.source_id,
        "source": complaint.source,
        "complaint_type": complaint.complaint_type,
        "descriptor": complaint.descriptor,
        "borough": complaint.borough,
        "status": complaint.status,
        "created_at": complaint.created_at,
        "latitude": complaint.latitude,
        "longitude": complaint.longitude,
        "score": score,
        "band": band,
        "age_days": age_days,
        "age_points": age_points,
        "category_points": category_points,
        "category_rule": rule_name,
        "explanation": explanation,
    }
