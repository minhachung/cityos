# CityOS — Urban Service Operations Intelligence

> **Phase 3 MVP (crew allocation simulator added).** Explore NYC 311 public records, inspect transparent rankings, and compare hypothetical crew assignments with a FIFO baseline. **No actual crews are dispatched.**

**Why this exists:** City service requests contain valuable signals about infrastructure and neighborhood demand. CityOS makes those public records explorable in one place, laying the groundwork for transparent prioritization and resource allocation algorithms.

## Features implemented

- React + TypeScript dashboard with search, borough/status filters, pagination, KPI cards, top categories, and an interactive Leaflet map.
- FastAPI + SQLAlchemy REST API backed by **SQLite by default** or PostgreSQL via `DATABASE_URL`.
- **Real data importer** for the official [NYC 311 public dataset](https://data.cityofnewyork.us/d/erm2-nwe9) (`erm2-nwe9`), using Socrata's API.
- **18 clearly identified fictional demo entries** so the project runs even without internet.
- Duplicate-safe ingestion, API error messages, and automated backend tests.
- **Experimental Priority Queue** ranks unresolved imported records using explicit category and report-age rules, showing score components and an optional demo-data toggle.
- **Fictional Crew Allocation Lab** uses exact maximum-weight bipartite matching under skill and straight-line distance constraints, compares results to oldest-first FIFO on the same pool, and displays assignment explanations.

**Important:** This is an independently built educational prototype, not NYC's operational system. The initial demo entries are synthetic; the product consistently labels their source. It does not dispatch crews, predict demand, or optimize routes. **The eight crew profiles and their locations, skills and capacities are entirely fictional.** Distances are straight-line approximations, not driving routes. Scores are NOT NYC policy, verified risk severity, or emergency triage.

## Quick start (macOS / Linux)

You need Python 3.11+ and Node.js 20+.

### Terminal 1 — backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./.venv/bin/python -m uvicorn app.main:app --reload --port 8001
```

API: http://localhost:8001/docs. If you use another port, update both targets in `frontend/vite.config.ts` accordingly.

### Terminal 2 — frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. The app uses the Vite proxy to connect to your local FastAPI server. The included `frontend/vite.config.ts` already targets port **8001**, leaving port 8000 free for Lighthouse.

Click **Sync NYC 311 data** to import the most recent 500 public service requests (requires internet). Repeat imports do not create duplicates. If the upstream service is unavailable, the app continues to work with demo data.

### Optional PostgreSQL

The backend defaults to SQLite so beginners can launch immediately. To switch to Postgres:

```bash
# from project root, requires Docker
 docker compose up -d db
# in backend terminal (before starting uvicorn)
export DATABASE_URL='postgresql+psycopg://cityos:cityos@localhost:5432/cityos'
```

Do not reuse the development database credentials on a public deployment.

## Tests

```bash
cd backend
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python -m pytest -q
```

## API

| Endpoint | Method | Description |
| --- | --- | --- |
| `/health` | GET | Health check |
| `/api/complaints` | GET | Filter, search and paginate stored records |
| `/api/stats` | GET | Counts grouped by category, borough and open/closed status |
| `/api/priorities?limit=10` | GET | Explainable rankings for matching unresolved stored NYC requests; supports `borough`, `q`, `include_demo` and `limit` (1–50) |
| `/api/allocation?crew_count=8&candidate_limit=60` | GET | Fictional crew matching vs. FIFO, using the same stored top-ranked candidate pool; supports borough/text/demo filters |
| `/api/ingest?limit=500` | POST | Fetch and insert latest NYC 311 records (max 1,000) |

Example: `GET /api/complaints?borough=BROOKLYN&status=Open&q=pothole&page=1&page_size=100`

## Architecture

```text
NYC Open Data API (Socrata)
          |
          v
  Python ingestion + normalization
          |
          v
 SQLite or PostgreSQL database
          |
          v
    FastAPI REST endpoints
          |
          v
 React / TypeScript / Leaflet UI
```

See [docs/architecture.md](docs/architecture.md) for key decisions, data provenance, and trade-offs.

Read [docs/ALLOCATION_ENGINE.md](docs/ALLOCATION_ENGINE.md) for the exact algorithm and honest benchmark limitations.

## Roadmap

- [x] Full-stack skeleton, API and database
- [x] Interactive map, filters, counts and table
- [x] Real public data ingestion + demo mode
- [x] Backend unit and API tests
- [x] Category-aware prioritization with explicit, testable rules
- [x] Fictional crew assignment optimizer with one-job/skill/geographic constraints
- [x] Side-by-side comparison against a first-in-first-out baseline on the same candidate pool
- [ ] Service-demand prediction evaluated out-of-sample
- [ ] Deployment, authentication and security hardening

## Project layout

```text
backend/app/       FastAPI, models, database and NYC 311 importer
backend/tests/     Automated Python tests
frontend/src/      React dashboard, API client and map
frontend/          Vite + TypeScript tooling
docs/              Architecture / engineering decisions
```

## What this project demonstrates

**Full-stack ownership:** frontend state, backend API, relational data modeling, external data ingestion, validation, and tests. The priority queue adds a documented decision-support heuristic. The allocation lab adds exact combinatorial optimization, explicit constraints, a reproducible FIFO benchmark, and test cases. Future work will validate assumptions and outcomes with appropriately sourced operational data.

### Dataset credit

Public records: [NYC 311 Service Requests from 2020 to Present](https://data.cityofnewyork.us/d/erm2-nwe9) (NYC Open Data), API fields include `complaint_type` and `descriptor` despite updated user-facing labels of *Problem* and *Problem Detail*.

Map tiles: CARTO / OpenStreetMap. For production use, follow tile attribution and usage requirements.

## Limitations / production considerations

- Public feed snapshots and statuses change; imported records are not automatically refreshed and are not guaranteed to reflect real-time service conditions.
- The current import route is intentionally **unauthenticated for local development**. Add authentication and rate limiting before exposing backend publicly.
- Queries and summaries cover only **the rows imported into your own database**, not all NYC service requests. The map renders up to 100 complaint points from the current page.
- Demo records are fictional and are not evidence of real civic requests. Priority rankings exclude them by default.
- **The prioritization weights are invented for education:** category 20–60 points plus report age 5 points/day (capped at 40); score is a review-order heuristic, not a verified severity measure. It excludes closed/resolved records but stored statuses may be stale; the scoring date uses UTC day precision.
- The app does not claim an official relationship with NYC agencies.
- **Allocation comparisons are simulated**: invented teams, invented qualifications, and straight-line distance proxies; neither method is a verified operational standard.
- The matching objective deliberately prioritizes the prototype score while penalizing distance. It is not a fairness, safety, or cost model; visit [docs/ALLOCATION_ENGINE.md](docs/ALLOCATION_ENGINE.md) for the details and limitations.

## Publish to GitHub

From this folder, after you've tested and reviewed the code:

```bash
git init -b main
git add .
git status --short  # review what will be committed: no .venv, node_modules, .env, or .db
git commit -m "Build CityOS operations intelligence MVP"
```

Then create a **new empty repository** named `cityos` in GitHub (do not initialize it with a README). Copy its URL and run:

```bash
git remote add origin https://github.com/YOUR_USERNAME/cityos.git
git push -u origin main
```

If `git remote add origin` says `remote origin already exists`, inspect `git remote -v` instead of adding it twice. If you use GitHub CLI and are signed in, you can instead run `gh repo create cityos --public --source=. --remote=origin --push`. Do not share an empty public repository as finished work; make your own changes first, then explain what you learned.

Start with [the step-by-step learning path](docs/LEARNING_PATH.md). A GitHub Actions workflow runs backend tests on pushes and pull requests.
