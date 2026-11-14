# Deploy CityOS as a public portfolio demo

The root `Dockerfile` builds the React UI and serves it from FastAPI on **one domain**. The `render.yaml` defines one free Render Docker web service.

## Deploy via Render Blueprint

1. Merge the deployment changes into GitHub `main`.
2. Sign in at [Render](https://dashboard.render.com/) and connect your GitHub account.
3. Choose **New → Blueprint**, select `minhachung/cityos`, branch `main`, with Blueprint path `render.yaml`.
4. Review the proposed **cityos-minhachung** web service and its Free instance plan, then deploy.
5. Once Render reports *Live*, open its allocated `https://...onrender.com/` URL. Do not assume its exact hostname until Render confirms it.
6. Check `/health`, `/api/stats`, `/api/priorities`, `/api/allocation`, and the dashboard at `/`.

## How the public demo works

- `CITYOS_PUBLIC_DEMO=1` imports up to 500 public NYC 311 records when the service starts. If the public data feed is unavailable, the app still opens using the clearly-labeled fictional examples.
- The public `POST /api/ingest` endpoint is **admin-only**. Without a configured password hash,
  it fails closed; anonymous visitors cannot trigger repeated imports.
- Configure `CITYOS_ADMIN_PASSWORD_HASH` as a **secret environment variable on Render**,
  following [Admin and map setup](ADMIN_AND_MAP.md). Never commit the value to GitHub.
- Local development without an admin password still supports manual sync. Keep using
  `backend` on port 8001 and `frontend` on port 5173 locally.
- The free Render service **spins down after inactivity**. Its local SQLite file is ephemeral: imported records are lost on restart, then imported again on startup. This deployment is a short-lived portfolio demonstration, **not** a persistent database or production system.
- As a result, do not claim the demo has continuous live synchronization or persistence. It shows a bounded current snapshot refreshed at each service startup.
- A production edition should use a durable PostgreSQL instance, scheduled ingestion, managed authentication/MFA, and distributed API rate limiting. Render free Postgres currently expires after 30 days, so this demonstration intentionally uses ephemeral SQLite instead.

## Verify locally

From the repository root:

```bash
cd backend
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python -m pytest -q
cd ../frontend
npm ci
npm run build
```

If you have Docker installed:

```bash
docker build -t cityos-demo .
docker run --rm -p 10000:10000 -e CITYOS_PUBLIC_DEMO=1 cityos-demo
```

Then open http://localhost:10000 and http://localhost:10000/health.

**Safety:** This is an educational simulation. Its urgency rules, fictional crews, and straight-line distances should never be used for real city dispatch or emergency response.
