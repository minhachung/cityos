# Crew allocation v0.3 — explainable optimization and fair benchmarking

## Important scope

This is an educational **simulation**, not a public-service dispatch tool. We use *real, imported NYC 311 request records* but **eight entirely fictional crews** with invented skills, locations, and one-job capacity. The app does not actually assign crews. The numeric priority score is our earlier student-defined age/category heuristic, **not official severity or emergency priority**.

## The engineering question

If you have only a small set of qualified crews, which requests should you propose for review first? We compare a **maximum-weight matching** algorithm against a simple **first-in-first-out** (FIFO) heuristic on **the same candidate pool**.

### Candidate selection

1. Load unresolved stored public 311 records (`closed` and `resolved` excluded).
2. Exclude records without latitude/longitude. Exclude fictional records by default.
3. Apply optional borough and text filters.
4. Score requests using the v0.2 `priority_for()` heuristic.
5. Sort by descending priority score, then report timestamp, then source ID, and take the first N (default 60, max 150).

The candidate pool is *not all NYC's complaints*—only the best-scored N records among those that you imported. Comparing on the same pool avoids one simple source of benchmark bias, but choosing a top-scored pool still limits what the comparison means.

### Eligibility constraints

A crew can be matched to a request only if:

- The crew's fictional skills include the request's mapped service group (`street`, `water`, `noise`, etc.).
- Crew base and report location are at most **25 km apart in straight-line / Haversine distance**. This is **not** drivable travel distance or duration.
- One request goes to at most one crew and each crew gets at most one request per run.

Requests with an unsupported category or no eligible crews remain unassigned. The prototype does not claim that the fictional skill classification corresponds to any NYC agency.

### Objective

For each eligible pair of request `r` and crew `c`:

```
benefit(r,c) = priority_score(r) - 1.0 * distance_km(c,r)
```

Choose compatible pairs to **maximize the sum of benefits**. A crew can remain idle if all eligible pairings have negative benefit.

- **Optimizer:** exact dynamic programming over crew bitmasks; complexity roughly `O(N × 2^C × C)` with `N <= 150`, `C <= 8`. For each bitmask of already-occupied crews, keep the best objective and a reconstruction of the chosen pairs. Processing requests one at a time prevents assigning the same request twice.
- **FIFO baseline:** traverse the *same* candidate pool by oldest report first, assign each request to its nearest remaining eligible crew, then stop once no further assignments are possible.

Because the optimizer maximizes this defined objective exactly (for the constrained pool), its objective should never be worse than FIFO. That does **not** prove better city operations, safety outcomes, true travel times, or social benefit. Both algorithms share the same unvalidated fictional assumptions.

## API

`GET /api/allocation?crew_count=8&candidate_limit=60`

Optional: `borough=BROOKLYN`, `q=water`, `include_demo=true`.

The response returns counts, assigned pairs and their explanations, total selected priority, total straight-line kilometers, both objective values, and the absolute objective difference. Change the number of crews (4 / 6 / 8) and number of candidates (30 / 60 / 100) in the UI.

## How to evaluate honestly

1. Run `python -m pytest -q` from `backend/`.
2. Import public 311 records and run the allocation simulation with a fixed crew count and pool size.
3. Record both objective scores and the number of assigned requests. Repeat with changed assumptions.
4. Discuss sensitivity to invented priorities, service-group mapping, maximum distance, and fictitious crew locations.
5. Consider a future version with validated agency data, actual road networks, crew shifts, geographic fairness constraints, and a human approval workflow.

No route planning, traffic information, or crew dispatch is implemented in v0.3.
