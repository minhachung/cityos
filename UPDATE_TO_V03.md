# CityOS v0.3 — Install the simulated crew allocation update

This package contains the **complete CityOS source code** so it works whether you're running v0.1 or v0.2. It excludes databases and environments, so your existing imported NYC 311 records stay on your Mac. It updates `frontend/vite.config.ts` to point to the CityOS backend on port **8001** (Lighthouse can keep 8000).

## Install in your existing project

Download `CityOS_Allocation_v03.zip` to your Downloads folder. Stop the running frontend/backend servers with `Ctrl+C` and then paste:

```bash
cd ~/Downloads/cityos
unzip -o ~/Downloads/CityOS_Allocation_v03.zip
```

Do **not** delete the existing project folder, and do **not** delete `backend/cityos.db`. The ZIP contains no `.db` files.

## Terminal 1 — backend

```bash
cd ~/Downloads/cityos/backend
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python -m pytest -q
./.venv/bin/python -m uvicorn app.main:app --reload --port 8001
```

Visit `http://127.0.0.1:8001/docs` and locate the new `GET /api/allocation` endpoint.

## Terminal 2 — frontend

```bash
cd ~/Downloads/cityos/frontend
npm install
npm run build
npm run dev
```

Open `http://localhost:5173`, then click **Crew allocation** in the sidebar. The panel compares an exact maximum-weight matching against FIFO using your imported request records and fictional crew definitions. Try changing the crew count and candidate pool size.

If a terminal command fails, copy the **first error message**, not just the last line.

## Publish on GitHub

See `README.md` (section **Publish to GitHub**) or follow the steps in the accompanying ChatGPT reply. Check `git status --short` before you commit. `.gitignore` intentionally excludes `.venv/`, `node_modules/`, `.env`, and `*.db`.

## Scope and safety

- Real NYC 311 public records; **fictional**, not operational, crews and capabilities.
- The candidate pool is limited to the stored, currently imported requests, not the entire city.
- Comparisons are against a synthetic objective, not measured improvement in real civic outcomes.
- The public sync endpoint has no authentication. This code is a local development prototype; do not deploy the backend publicly unchanged.
