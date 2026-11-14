# CityOS v0.4 — private admin access and public basemap

CityOS remains publicly explorable. Only the owner can trigger ingestion of new NYC 311 data.
The crew allocation algorithm still simulates fictional resources; it does not dispatch anyone.

## Why the map was watermarked

The old `light_all` raster basemap from CARTO started requiring an API key in 2026.
The Leaflet map now loads standard OpenStreetMap tiles from
`https://tile.openstreetmap.org/{z}/{x}/{y}.png` with visible OSM attribution.
This works without your own key for a small public demo, subject to the
[OSMF tile usage policy](https://operations.osmfoundation.org/policies/tiles/).
Do not bulk-fetch tiles; if the site grows, choose a tile service with an appropriate plan.

## Configure the single-owner admin password

**Never commit a password or its hash to GitHub.** The helper prompts you privately on your own machine.

1. Install the v0.4 update and push it to GitHub, then run:

   ```bash
   cd ~/Downloads/cityos
   ./backend/.venv/bin/python scripts/create_admin_hash.py
   ```

   If you don't have that local virtual environment, create it as described in the root README.
   Choose a unique password of at least 14 characters and confirm it.

2. Copy **only the generated hash** (starts with `pbkdf2_sha256$`).
3. On Render, open the existing service **cityos-minhachung** → **Environment**.
   Add `CITYOS_ADMIN_PASSWORD_HASH` with that value. Keep `CITYOS_PUBLIC_DEMO=1`.
   Save and redeploy/restart if Render doesn't deploy automatically.
4. On `https://cityos-minhachung.onrender.com`, choose **Admin sign in**.
   Enter your **original password**, *not* the generated hash. The button for
   **Sync NYC 311 data** will become available only to you.
5. Use **Sign out** when done. If your free Render service sleeps/restarts, you'll need to log in again.

Do not share the password or hash in chat. Do not put a password or a `.env` file in GitHub.

## Security properties

- Public GET data and simulation APIs work without login.
- Public demo's ingestion POST requires an authenticated session and a custom request header;
  it is denied when the admin hash is not configured.
- Passwords are verified against a salted PBKDF2-SHA256 hash (600,000 rounds), with constant-time comparison.
- On successful login, an opaque high-entropy session ID is stored only as a SHA-256 digest in
  process memory; the browser receives an `HttpOnly`, `Secure`, `SameSite=Strict` cookie.
- Sessions expire after 4 hours or on logout; a service restart invalidates sessions.
- Login attempts are limited to 5 failures per 15 minutes per observed client address
  **in the current process**. This does not replace distributed rate limiting or an identity provider.
- Admin mutation routes require the custom header and reject mismatching Origin values.
- The public NYC dataset is still fetched on service boot, and SQLite remains ephemeral
  on Render Free. Manual sync is for the owner only, not scheduled persistence.

This is a deliberately **single-admin prototype**, not a production identity system. Before
real-world deployment, use managed authentication with MFA, persistent/shared session and rate-limit
stores, audit logging, HTTPS enforced at the gateway, monitoring, and a durable database.

## Local test

```bash
cd ~/Downloads/cityos/backend
./.venv/bin/python -m pytest -q
cd ../frontend
npm run build
```

To try the sign-in flow locally, set `CITYOS_ADMIN_PASSWORD_HASH` in your backend
shell before starting Uvicorn. Without this setting, local development still permits
unauthenticated syncing to keep the original MVP workflow intact. **The public Render
service never permits anonymous syncing, even if the admin hash is missing.**
