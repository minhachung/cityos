"""Allocation optimizer: valid matching, reproducible comparison, and API constraints."""
from datetime import date, datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.allocation import allocate, service_group
from app.db import Base, get_db
from app.main import app
from app.models import Complaint


def req(key, kind, day, *, lat=40.75, lon=-73.98, source='nyc311', status='Open'):
    return Complaint(source_id=key, source=source, created_at=datetime(2026, 11, day),
                     complaint_type=kind, descriptor='Test record', borough='MANHATTAN',
                     status=status, latitude=lat, longitude=lon)


def test_service_group_labels():
    assert service_group('Noise - Residential') == 'noise'
    assert service_group('Illegal Parking') == 'parking'
    assert service_group('Street Light Condition') == 'lighting'
    assert service_group('HEAT/HOT WATER') == 'water'
    assert service_group('Unknown category') == 'other'


def test_fifo_matches_optimum_when_oldest_is_also_best():
    rows = [req('old-noise', 'Noise - Residential', 1),
            req('new-parking', 'Illegal Parking', 14)]
    result = allocate(rows, date(2026, 11, 14), crew_count=1)
    assert result['fifo']['assignments'][0]['source_id'] == 'old-noise'
    assert result['optimized']['assignments'][0]['source_id'] == 'old-noise'
    assert abs(result['objective_gain']) < 0.01


def test_optimizer_selects_higher_utility_over_older_request():
    rows = [req('old-noise', 'Noise - Residential', 13),
            req('new-parking', 'Illegal Parking', 14)]
    r = allocate(rows, date(2026, 11, 14), crew_count=1)
    assert r['fifo']['assignments'][0]['source_id'] == 'old-noise'
    assert r['optimized']['assignments'][0]['source_id'] == 'new-parking'
    assert r['objective_gain'] > 0


def test_unique_crews_unique_requests_skill_distance_and_unmapped():
    rows = [req('parking', 'Illegal Parking', 13),
            req('noise', 'Noise - Residential', 14),
            req('road', 'Street Condition', 13, lat=40.69, lon=-73.95),
            req('far', 'Illegal Parking', 13, lat=35.0, lon=-80.0),
            req('missing', 'Noise', 13, lat=None, lon=None),
            req('closed', 'Water System', 1, status='Closed')]
    r = allocate(rows, date(2026, 11, 14), crew_count=4)
    assert r['unresolved_stored'] == 5
    assert r['unmapped_skipped'] == 1
    assert r['considered'] == 4
    for variant in ('optimized', 'fifo'):
        assignments = r[variant]['assignments']
        assert len({x['crew_id'] for x in assignments}) == len(assignments)
        assert len({x['source_id'] for x in assignments}) == len(assignments)
        assert all(x['distance_km'] <= 25 for x in assignments)
        assert all(x['service_group'] in x['crew_skills'] for x in assignments)
    assert r['objective_gain'] >= -0.01
    assert not any(a['source_id'] == 'far' for a in r['optimized']['assignments'])


def test_empty_candidates_and_validation():
    assert allocate([], date(2026, 11, 14))['optimized']['assigned_count'] == 0
    for bad in (0, 9):
        try:
            allocate([], date(2026, 11, 14), crew_count=bad)
            assert False
        except ValueError:
            pass


def test_allocation_endpoint_filters_and_validates():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    with sessions() as db:
        db.add_all([
            req('1', 'Illegal Parking', 13),
            req('2', 'Noise - Commercial', 13, source='demo'),
            req('3', 'Street Condition', 13, status='Closed'),
        ])
        db.commit()

    def override():
        with sessions() as db:
            yield db

    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override
    try:
        with TestClient(app) as client:
            result = client.get('/api/allocation', params={'crew_count': 4}).json()
            assert result['unresolved_stored'] == 1
            assert result['considered'] == 1
            assert result['optimized']['assigned_count'] == 1
            assert result['fifo']['assigned_count'] == 1
            assert 'fictional' in result['methodology']
            assert client.get('/api/allocation?include_demo=true').json()['unresolved_stored'] == 2
            assert client.get('/api/allocation?crew_count=0').status_code == 422
            assert client.get('/api/allocation?candidate_limit=151').status_code == 422
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous
        engine.dispose()
