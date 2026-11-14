# Learn CityOS by building it (not by memorizing generated code)

This repository provides a working starting point; use it as a scaffold. Your goal is to understand every significant file and make several substantive changes yourself.

## Session 1 — Understand the data flow (60–90 minutes)

1. Run the backend and open `http://localhost:8001/docs`.
2. Call `GET /api/complaints`, then `GET /api/stats`.
3. Trace one request through `main.py` → `db.py` → `models.py` → JSON response.
4. Explain the difference between the DB model (`Complaint`) and the response model (`ComplaintOut`).
5. Run `python -m pytest -q`, inspect `test_list_filters`, then add your own assertion for the Queens borough.

**Checkpoint:** Can you explain why `page_size` has a maximum of 500, and what would happen if it didn't?

## Session 2 — Understand frontend state (60–90 minutes)

1. Run the React frontend.
2. Type "pothole" in the search box; watch the browser network tab.
3. Trace the `search` state → debounced `query` → `URLSearchParams` → `api.ts` → backend query.
4. Try changing the filter while a request is slow. Explain the `active` flag in `useEffect`.
5. Independently implement a **Reset filters** button.

**Checkpoint:** Why do map points and KPI totals sometimes represent different amounts of data?

## Session 3 — Work with messy real data (60–90 minutes)

1. Click "Sync NYC 311 data"; verify the demo vs. real labels.
2. Read `ingest.py` and identify all assumptions made by `normalize`.
3. Extend unit tests to cover missing longitude, unexpected statuses, and empty descriptor.
4. Independently add a user-facing **source** filter (all / demo / NYC 311).

**Checkpoint:** Why must the importer be idempotent? Why shouldn't a government dataset be treated as error-free?

## Session 4 — Make it your own (2–4 hours)

Pick one meaningful extension and implement it without pasting an entire AI-generated file:

- Add a `GET /api/timeseries` endpoint grouped by day, then build a chart.
- Implement a clean switch to exclude demo data from all analysis once real records exist.
- Add timestamp-based incremental data ingestion so repeated syncs fetch new records only.
- Add a priority score *as a documented prototype*, with explicit rules and limitations.

**Checkpoint:** Write a short `docs/decisions.md` describing the problem, two possible solutions, trade-offs, and why you chose your approach.

## Session 5 — Explain your optimizer (60–90 minutes)

1. Read `docs/ALLOCATION_ENGINE.md` and trace a request through `service_group()` and `priority_for()`.
2. Draw the allowed edges between 4 fictional crews and 6 requests. Explain why skill and distance constraints matter.
3. In `allocation.py`, explain what the crew bitmask represents and why the algorithm cannot assign one request twice.
4. Compare a 4-crew run against FIFO. Change a crew's capabilities and predict the difference before running the tests.
5. Run `./.venv/bin/python -m pytest -q` and add a test where a location is over the distance limit.

**Checkpoint:** Can you explain why outperforming FIFO on an invented objective is **not** evidence of improved actual city service? How would you validate this with operations experts?

## Interview questions you should be able to answer

- What happens when NYC Open Data is unreachable or rate-limits your app?
- What SQL indexes did you create and why?
- How would this app scale from 500 to 10 million records?
- How would you keep request statuses fresh?
- How do you distinguish demo records from official records?
- Which metric would demonstrate that the platform saves time for an actual operator?
- What did you personally implement or change, and why?

## First Git commit

```bash
git init
git add .
git commit -m "Build CityOS full-stack MVP with NYC 311 ingestion"
```

Push only after reviewing all files and confirming there are no local database files or secrets being tracked. `.gitignore` excludes them.
