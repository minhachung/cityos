# CityOS

**Exploring NYC service requests and experimenting with better ways to prioritize them.**

CityOS is a full-stack web app I'm developing around NYC's public 311 service-request data. The idea started with a simple question: if a city has more problems reported than it can address at once, how should it decide what to look at first?

The app started as a way to explore complaint data on a map. I've since added a transparent priority system and a small crew-assignment simulation to test how different allocation strategies behave.

> **Project status:** Working local prototype. The 311 records are real public data; the priority rules and crews are hypothetical. CityOS is not affiliated with NYC and does not dispatch anyone.

## What it does

- **Explore complaints:** Search and filter requests by borough, status, and complaint type, then view geocoded reports on an interactive map.
- **Import public data:** Pull recent records from NYC Open Data into a local database. Re-importing doesn't create duplicate records.
- **Rank unresolved requests:** Generate 0–100 priority scores using clearly defined category and age rules. Each score comes with an explanation.
- **Simulate crew assignments:** Match requests to fictional crews based on skills, location, and one-job capacity.
- **Compare approaches:** Put the optimized assignments next to a first-in-first-out (oldest-first) baseline on the same candidate pool.

## Tech stack

| Part | Tools |
| --- | --- |
| Frontend | React, TypeScript, Vite, Leaflet |
| Backend | Python, FastAPI, SQLAlchemy |
| Database | SQLite locally; optional PostgreSQL |
| Data source | NYC Open Data / Socrata API |
| Testing | Pytest, GitHub Actions |

## How the allocation works

I wanted the allocation feature to do more than sort a list. For each unresolved request with coordinates, the app checks which fictional crews are eligible to handle it.

A crew is eligible only if it has the matching service category and is within **25 km straight-line distance** of the reported location. Each crew can take one request per simulation run, and each request can be assigned once.

For eligible pairs, the prototype calculates:

`assignment value = complaint priority score - distance in kilometers`

The optimizer uses **dynamic programming over crew bitmasks** to find the highest-total-value assignment among the selected requests. The baseline processes those same requests oldest-first and picks the nearest available eligible crew.

This comparison measures the model's *own scoring objective*, not real-world service quality. The crew skills, locations, and capacity are made up, and straight-line distance isn't drive time. See [the allocation notes](docs/ALLOCATION_ENGINE.md) for the full methodology and trade-offs.

## Run it locally

You'll need Python 3.11+ and Node.js 20+.

**1. Start the API**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8001
```

API documentation: http://localhost:8001/docs

**2. Start the frontend** in another terminal

```bash
cd frontend
npm install
npm run dev
```

Dashboard: http://localhost:5173

The app starts with labeled sample requests, so it works before you import anything. Use **Sync NYC 311 data** to pull real public records. The frontend's Vite proxy is configured for backend port `8001`.

**3. Run the backend tests**

```bash
cd backend
./.venv/bin/python -m pytest -q
```

## Main API routes

| Route | Purpose |
| --- | --- |
| `GET /api/complaints` | Search, filter, and paginate complaints |
| `GET /api/stats` | Summarize the currently stored records |
| `GET /api/priorities` | Return ranked unresolved requests with score breakdowns |
| `GET /api/allocation` | Compare crew matching with the FIFO baseline |
| `POST /api/ingest` | Import recent NYC 311 records |

## Project structure

```text
cityos/
├── backend/
│   ├── app/          # API, database, importer, scoring, allocation
│   └── tests/        # API and algorithm tests
├── frontend/
│   └── src/          # Dashboard, API client, interactive map
├── docs/             # Architecture and algorithm decisions
└── .github/workflows # Backend test workflow
```

## Current limitations and next steps

The current database is just a local snapshot of imported requests, not the full NYC 311 dataset. The prioritization weights are experimental, not validated urgency ratings. The crew simulation uses invented resources and approximate distances; it should **never be used for real emergency response or dispatch**. The import endpoint also needs authentication and rate limiting before any public deployment.

What I'd like to work on next:

- [ ] Evaluate priority rules against better-defined service outcomes
- [ ] Add road-network travel times and more realistic scheduling constraints
- [ ] Test how sensitive assignments are to different scoring weights
- [ ] Deploy a safe public demo with restricted data-import access

## Data and mapping credits

- [NYC 311 Service Requests](https://data.cityofnewyork.us/d/erm2-nwe9) — NYC Open Data
- Map tiles and geographic data — CARTO / OpenStreetMap (see attribution in the app)