# CityOS 0.2 — Add the experimental priority queue

This update overwrites only source and documentation files. It **does not contain or replace** `backend/cityos.db`, so your imported NYC 311 records stay on your Mac.

## Update your existing project on macOS

If you saved `CityOS_Priority_Update.zip` in Downloads, run this from a terminal:

```bash
cd ~/Downloads/cityos
unzip -o ~/Downloads/CityOS_Priority_Update.zip
```

To restart the backend (press Ctrl+C in the existing backend terminal first):

```bash
cd ~/Downloads/cityos/backend
./.venv/bin/python -m uvicorn app.main:app --reload --port 8001
```

To restart the frontend (press Ctrl+C in the existing frontend terminal first):

```bash
cd ~/Downloads/cityos/frontend
npm run dev
```

Go to http://localhost:5173 and select **Priority queue** in the sidebar.

## Verify

- http://127.0.0.1:8001/api/priorities?limit=3 — returns an explainable JSON ranking
- http://localhost:5173 — new priority queue appears after the map and category chart
- From `backend/`, run `./.venv/bin/python -m pytest -q`; ten automated tests should pass

**Port note:** This patch intentionally does **not** overwrite `frontend/vite.config.ts`, preserving your existing change from port 8000 to port 8001 (Lighthouse can continue using 8000).

Scores are a student-defined, experimental heuristic, **not** official NYC risk or emergency priorities.
