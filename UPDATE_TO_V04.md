# CityOS v0.4 — Map fix + private admin login

This is a source-only patch for the existing `~/Downloads/cityos` folder.
It **does not** contain or overwrite `backend/cityos.db`, `.venv`, `node_modules`, `README.md`,
Dockerfile, or `render.yaml`.

## Install and push

1. Download `CityOS_Admin_Map_v04.zip` to `~/Downloads`.
2. In Terminal:

   ```bash
   cd ~/Downloads/cityos
   unzip -o ~/Downloads/CityOS_Admin_Map_v04.zip
   cd backend
   ./.venv/bin/python -m pytest -q
   cd ../frontend
   npm run build
   cd ..
   git status --short
   git add backend/app/auth.py backend/app/main.py backend/tests/test_admin.py backend/tests/test_deployment.py frontend/src/MapView.tsx frontend/src/App.tsx frontend/src/AdminControls.tsx frontend/src/api.ts frontend/src/types.ts frontend/src/style.css scripts/create_admin_hash.py docs/ADMIN_AND_MAP.md docs/DEPLOY.md UPDATE_TO_V04.md
   git commit -m "Add admin-only NYC 311 sync and fix map tiles"
   git push origin main
   ```

3. Render automatically deploys the pushed code (if automatic deploys remain enabled).
4. Your map should display without CARTO's watermark. Force-refresh the browser if old tiles remain cached.

## Activate your private admin login

1. Generate a hash locally; your password will not be displayed or sent to ChatGPT:

   ```bash
   cd ~/Downloads/cityos
   ./backend/.venv/bin/python scripts/create_admin_hash.py
   ```

2. Open [the existing Render service](https://dashboard.render.com/web/srv-dbscbes9v7es73cag62g)
   → **Environment**, add this environment variable:

   Name: `CITYOS_ADMIN_PASSWORD_HASH`
   Value: the entire printed `pbkdf2_sha256$...` hash.

   Do **not** replace `CITYOS_PUBLIC_DEMO=1`. Do **not** paste your password or hash into chat or GitHub.

3. Save; allow Render to redeploy/restart with the new environment variable.
4. On https://cityos-minhachung.onrender.com/ click **Admin sign in**, enter your chosen
   *password* (not the hash), and then **Sync NYC 311 data**.
5. Use **Sign out** when done. Sessions are reset when the free server restarts.

## Scope and limitations

- Public visitors still can explore requests and run hypothetical priority/crew simulations.
- Only authenticated admins can manually refresh NYC 311 on the hosted version.
- The password is stored as a salted hash in Render environment, not code. Sessions use a
  short-lived, HTTP-only secure cookie and an in-memory session list; a single admin only.
- The basemap switches from key-requiring CARTO tiles to standard OpenStreetMap tiles.
  Respect https://operations.osmfoundation.org/policies/tiles/.
- NYC snapshot is still stored in temporary SQLite on Render's free tier.
- CI checks backend tests and frontend build after a push. Do not share a site publicly
  before checking the actual deployed UI works.

See `docs/ADMIN_AND_MAP.md` for the complete design and threat-model limitations.
