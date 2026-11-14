"""Educational, exact maximum-weight assignment of a small group of fictional crews.

A maximum-weight bipartite matching is solved with dynamic programming over crew
bitmasks. This is suitable for <= 8 crews and <= 150 candidate requests.

Important: These are *fictional* crews, fictional skill labels, and straight-line
proxies for distance. This is not a municipal dispatch system.
"""
from dataclasses import dataclass
from datetime import date
from math import asin, cos, radians, sin, sqrt
from .models import Complaint
from .priority import priority_for


@dataclass(frozen=True)
class Crew:
    code: str
    name: str
    skills: frozenset[str]
    latitude: float
    longitude: float


# All these teams are fictional and have a capacity of ONE assignment per run.
# The first four include a mixture of competencies for a meaningful smaller demo.
CREWS = (
    Crew('C01', 'Manhattan Community', frozenset({'noise', 'parking', 'other'}), 40.755, -73.985),
    Crew('C02', 'Brooklyn Street Works', frozenset({'street', 'lighting'}), 40.678, -73.946),
    Crew('C03', 'Queens Waterworks', frozenset({'water', 'sewer'}), 40.728, -73.795),
    Crew('C04', 'Bronx Civic Response', frozenset({'parking', 'noise', 'other'}), 40.832, -73.902),
    Crew('C05', 'Manhattan Street Works', frozenset({'street', 'lighting'}), 40.731, -73.995),
    Crew('C06', 'Brooklyn Community', frozenset({'parking', 'noise', 'other'}), 40.696, -73.988),
    Crew('C07', 'Staten Island Sanitation', frozenset({'sanitation', 'street'}), 40.593, -74.144),
    Crew('C08', 'Queens Utilities & Sanitation', frozenset({'water', 'sewer', 'sanitation'}), 40.749, -73.870),
)
MAX_DISTANCE_KM = 25.0
DISTANCE_PENALTY_PER_KM = 1.0


def service_group(kind: str) -> str:
    """Illustrative text grouping, not an official 311 agency mapping."""
    text = kind.strip().lower()
    if text.startswith(('water system', 'water ', 'heat/hot water')):
        return 'water'
    if text.startswith('sewer'):
        return 'sewer'
    if text.startswith('street light'):
        return 'lighting'
    if text.startswith(('street condition', 'pothole', 'sidewalk')):
        return 'street'
    if text.startswith(('sanitation', 'dirty conditions', 'overflowing litter', 'missed collection')):
        return 'sanitation'
    if text.startswith(('illegal parking', 'blocked driveway')):
        return 'parking'
    if text.startswith('noise'):
        return 'noise'
    return 'other'


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance, NOT drivable road distance or travel time."""
    a, b, c, d = map(radians, (lat1, lon1, lat2, lon2))
    delta_lat, delta_lon = c-a, d-b
    hav = sin(delta_lat/2)**2 + cos(a)*cos(c)*sin(delta_lon/2)**2
    return 6371.0088 * 2 * asin(min(1, sqrt(hav)))


def _assignment(crew: Crew, record: dict, distance: float) -> dict:
    utility = record['score'] - DISTANCE_PENALTY_PER_KM * distance
    return {
        'crew_id': crew.code,
        'crew_name': crew.name,
        'crew_skills': sorted(crew.skills),
        'source_id': record['source_id'],
        'complaint_type': record['complaint_type'],
        'borough': record['borough'],
        'created_at': record['created_at'].isoformat(),
        'priority_score': record['score'],
        'service_group': record['service_group'],
        'distance_km': round(distance, 2),
        'utility': round(utility, 2),
        'reason': f"Capability '{record['service_group']}', score {record['score']} less {distance:.1f} km straight-line distance penalty.",
    }


def _summary(pairs: tuple[tuple[int, int], ...], crews: tuple[Crew, ...],
             requests: list[dict], eligible: dict[tuple[int, int], float]) -> dict:
    assignments = sorted(
        [_assignment(crews[crew_index], requests[request_index], eligible[(request_index, crew_index)])
         for request_index, crew_index in pairs],
        key=lambda a: a['crew_id'],
    )
    return {
        'assigned_count': len(assignments),
        'total_priority': sum(a['priority_score'] for a in assignments),
        'total_distance_km': round(sum(eligible[(ri, ci)] for ri, ci in pairs), 2),
        'objective': round(sum(requests[ri]['score'] - DISTANCE_PENALTY_PER_KM * eligible[(ri, ci)]
                               for ri, ci in pairs), 2),
        'assignments': assignments,
    }


def allocate(complaints: list[Complaint], as_of: date, crew_count: int = 8,
             candidate_limit: int = 60) -> dict:
    """Optimize against FIFO on the EXACT SAME top-ranked candidate pool.

    The optimizer maximizes the sum of (priority score - straight-line km),
    subject to one request per crew, one crew per request, matching category skills,
    and a maximum straight-line distance. The baseline visits the same candidates
    oldest first, choosing the nearest available eligible crew.
    """
    if not 1 <= crew_count <= len(CREWS):
        raise ValueError('crew_count must be between 1 and 8')
    if not 1 <= candidate_limit <= 150:
        raise ValueError('candidate_limit must be between 1 and 150')
    crews = CREWS[:crew_count]
    # Extra defensive filtering for callers that do not use the API endpoint.
    unresolved = [c for c in complaints if c.status.strip().lower() not in {'closed', 'resolved'}]
    unmapped_count = sum(c.latitude is None or c.longitude is None for c in unresolved)
    records = [priority_for(c, as_of) for c in unresolved
               if c.latitude is not None and c.longitude is not None]
    for r in records:
        r['service_group'] = service_group(r['complaint_type'])
    records.sort(key=lambda r: (-r['score'], r['created_at'], r['source_id']))
    candidate_pool = records[:candidate_limit]

    eligible: dict[tuple[int, int], float] = {}
    for ri, req in enumerate(candidate_pool):
        for ci, crew in enumerate(crews):
            if req['service_group'] not in crew.skills:
                continue
            dist = distance_km(crew.latitude, crew.longitude, req['latitude'], req['longitude'])
            if dist <= MAX_DISTANCE_KM and req['score'] - DISTANCE_PENALTY_PER_KM * dist > 0:
                eligible[(ri, ci)] = dist

    # Exact dynamic programming: for each bitmask of occupied crews, retain the
    # best utility and its assignments. Processing each request once prevents
    # the same request from being assigned twice.
    dp: dict[int, tuple[float, tuple[tuple[int, int], ...]]] = {0: (0.0, ())}
    for ri, req in enumerate(candidate_pool):
        next_dp = dict(dp)  # Skip this request.
        for mask, (value, pairs) in dp.items():
            for ci in range(crew_count):
                dist = eligible.get((ri, ci))
                if mask & (1 << ci) or dist is None:
                    continue
                new_mask = mask | (1 << ci)
                new_value = value + req['score'] - DISTANCE_PENALTY_PER_KM * dist
                prior = next_dp.get(new_mask)
                if prior is None or new_value > prior[0] + 1e-9:
                    next_dp[new_mask] = (new_value, pairs + ((ri, ci),))
        dp = next_dp
    _, best_pairs = max(dp.values(), key=lambda state: (state[0], len(state[1])))

    # FIFO benchmark: oldest first, choose nearest matching remaining crew.
    available = set(range(crew_count))
    fifo_pairs = []
    for ri in sorted(range(len(candidate_pool)),
                     key=lambda i: (candidate_pool[i]['created_at'], candidate_pool[i]['source_id'])):
        choices = [(dist, ci) for ci in available
                   if (dist := eligible.get((ri, ci))) is not None]
        if choices:
            _, ci = min(choices)
            available.remove(ci)
            fifo_pairs.append((ri, ci))

    optimized = _summary(best_pairs, crews, candidate_pool, eligible)
    fifo = _summary(tuple(fifo_pairs), crews, candidate_pool, eligible)
    return {
        'as_of': as_of.isoformat(),
        'crew_count': crew_count,
        'candidate_limit': candidate_limit,
        'unresolved_stored': len(unresolved),
        'unmapped_skipped': unmapped_count,
        'considered': len(candidate_pool),
        'eligible_requests': len({ri for ri, _ in eligible}),
        'optimized': optimized,
        'fifo': fifo,
        'objective_gain': round(optimized['objective'] - fifo['objective'], 2),
        'methodology': (
            'Educational simulation only. Crew locations, skills and capacity are fictional. '
            'Candidate pool is the top-ranked geocoded unresolved records stored locally, NOT all NYC 311 reports. '
            'Both methods use the identical pool. Each crew can handle at most one request; '
            'category skills must match and straight-line distance must be <= 25 km. '
            'Exact max-weight matching maximizes score minus 1 point per straight-line km; '
            'FIFO processes oldest first and assigns the nearest eligible crew. '
            'Distance is NOT road travel time. Not for actual dispatch or emergencies.'
        ),
    }
