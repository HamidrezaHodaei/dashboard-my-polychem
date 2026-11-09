# PolyChem Automation System — Backend (Phase 0)

Flask backend foundation for the PolyChem centralized internal automation
platform. **This is Phase 0 only** — an application skeleton with a health
endpoint. No authentication, RBAC, organizational hierarchy, or business
modules exist yet. See `IMPLEMENTATION_PLAN.md` for what comes next.

The existing CRM (`crm.polychemmb.com`) and existing APIs
(`api.polychemmb.com`) are untouched — this backend does not connect to
them in Phase 0 (or, in fact, until the relevant integration-adapter phase).

---

## 1. Python version

Python **3.12+** is required.

```powershell
python --version
```

## 2. Create a virtual environment

**Windows (PowerShell):**
```powershell
cd polychem-automation-backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks the activation script, run once (as your user, not admin):
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

**macOS / Linux:**
```bash
cd polychem-automation-backend
python3 -m venv .venv
source .venv/bin/activate
```

## 3. Install dependencies

```powershell
pip install -r requirements.txt
```

## 4. Create the local MySQL database

Requires a local MySQL 8.x server running on `localhost:3306`. This backend
uses its **own** database — it must never point at, modify, or share
tables with the existing CRM database.

```powershell
mysql -u root -p -e "CREATE DATABASE polychem_automation CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

(Adjust the `-u`/`-p` flags to your local MySQL credentials.)

## 5. Configure environment variables

Copy the example file and fill in your real local values:

**Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

**macOS / Linux:**
```bash
cp .env.example .env
```

Then edit `.env` and set `DATABASE_URL` to your local MySQL credentials, e.g.:
```
DATABASE_URL=mysql+pymysql://root:yourpassword@localhost:3306/polychem_automation
```

`.env` is git-ignored — never commit real credentials. Only `.env.example`
(placeholders) is tracked.

## 6. Run migrations

Phase 0 ships a single **empty** migration — no business tables exist yet.
This step verifies your MySQL connection and Alembic setup work end to end.

```powershell
flask db upgrade
```

(`flask db init` and `flask db migrate` have already been run to produce
the `migrations/` folder and the initial empty revision checked into this
repo — you shouldn't need to re-run them unless you're regenerating
migrations from scratch.)

## 7. Run the Flask server

```powershell
python run.py
```

Serves on **http://localhost:5000**.

## 8. Run tests

```powershell
pytest
```

Tests use `TestingConfig`, which runs against an in-memory SQLite database
— **no live MySQL server is required to run the test suite.** This keeps
the suite fast and independent of local environment setup.

## 9. Health endpoint

```
GET http://localhost:5000/api/health
```

Example response:
```json
{
  "success": true,
  "data": {
    "status": "ok",
    "database": "connected"
  }
}
```

If the database is unreachable, `status` reports `"degraded"` and
`database` reports `"unavailable"` — the endpoint itself still returns
`200` (it's reporting on health, not failing the request), and no
connection details (host/user/password) are ever included in the response.

## 10. Current Phase 0 limitations

This is intentionally a minimal foundation. **Not yet implemented:**
- No authentication (login/JWT/sessions) — Phase 3
- No RBAC / permissions / scope engine — Phase 2
- No `users`, `roles`, `permissions`, `organizations`, `departments`,
  `teams`, or any business tables — Phase 1 onward
- No Tasks, CRM, Finance, Warehouse, Mail, Customer Panel, Website
  Management, or Visitor Statistics modules
- No integration adapters or outbound calls to `crm.polychemmb.com` /
  `api.polychemmb.com`
- No production deployment — no Gunicorn, no reverse proxy, no production
  secrets or CORS configuration. `wsgi.py` exists as a placeholder only.
- Rate limiting (Flask-Limiter) is initialized but carries only a generic
  default limit — auth-specific brute-force limits come with Phase 3.

**What Phase 0 does provide:**
- A working Application Factory (`create_app()`) with Development/Testing/
  Production config classes
- SQLAlchemy + Flask-Migrate wired to MySQL (via PyMySQL) locally
- `GET /api/health` with a best-effort DB connectivity check
- Consistent JSON success/error response envelope, including 400/404/405/500
- Request ID generation + propagation (`X-Request-ID`)
- Basic structured request logging (method, path, status, request ID,
  duration — never credentials/tokens/secrets)
- CORS locked to `http://localhost:3000`, no wildcard
- A passing pytest suite covering all of the above

See `ARCHITECTURE.md`, `DATABASE.md`, `AUTHORIZATION.md`, `API.md`,
`INTEGRATIONS.md`, `SECURITY.md`, and `IMPLEMENTATION_PLAN.md` for the full
design this foundation builds toward.
