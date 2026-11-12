# Running FinTrack locally

This guide covers running FinTrack on your machine without Docker. You'll start PostgreSQL, create the tables, then run the backend (FastAPI) and the frontend (React + Vite).

Run each long-running command in its own terminal. Every command starts from the repository root.

## 1. Prerequisites

| Tool | Version | Used for |
|---|---|---|
| Python + [uv](https://docs.astral.sh/uv/) | Python 3.13, uv 0.10 or later | Backend |
| Node.js + npm | Node 24 | Frontend |
| PostgreSQL server binaries (`initdb`, `pg_ctl`, `psql`) | 16 or later | Database |
| [Mailpit](https://mailpit.axllent.org/) (optional) | any | Shows password-reset emails |

The scripts look for PostgreSQL in `/Library/PostgreSQL/18/bin`, the EDB installer's default location. If yours is somewhere else, set `PGBIN`, for example `PGBIN=/opt/homebrew/opt/postgresql@16/bin`.

## 2. Start the database

```bash
scripts/dev-db.sh start
```

The first run creates a local cluster in `.local/pgdata`, listening on port **54329**. It also creates:

| Name | Kind | Purpose |
|---|---|---|
| `fintrack` | role, password `fintrack` | Owns the schema and runs migrations |
| `fintrack_app` | role, password `fintrack_app` | Used by the API at runtime. It has limited rights: for example, it can't edit or delete the audit log. |
| `fintrack` | database | Development data |
| `fintrack_test` | database | Used by the backend test suite. The tests rebuild it on every run. |

Later runs only restart the server.

Other database commands:

```bash
scripts/dev-db.sh status   # is it running?
scripts/dev-db.sh stop     # stop the server
scripts/dev-db.sh reset    # WARNING: deletes all local data and recreates the empty cluster
```

### Connection details

| Use | Connection string |
|---|---|
| API (`DATABASE_URL`) | `postgresql+psycopg://fintrack_app:fintrack_app@localhost:54329/fintrack` |
| Migrations (`MIGRATION_DATABASE_URL`) | `postgresql+psycopg://fintrack:fintrack@localhost:54329/fintrack` |
| psql or a GUI client (DBeaver, TablePlus, …) | `postgresql://fintrack:fintrack@localhost:54329/fintrack` |

The `+psycopg` part tells SQLAlchemy which driver to use. Leave it out for any other client.

`psql` might not be on your `PATH`. If so, call it by its full path:

```bash
/Library/PostgreSQL/18/bin/psql postgresql://fintrack:fintrack@localhost:54329/fintrack
```

These passwords are for local development only. Never reuse them in a shared or production environment.

## 3. Configure the backend (optional)

The backend's built-in development defaults already match the database above. Create an env file only if you need to change a setting:

```bash
cp .env.example backend/.env
```

The backend reads `backend/.env`. All settings are listed in `.env.example` and in the README's configuration table.

## 4. Create the tables (migrations)

```bash
cd backend
uv sync                      # install Python dependencies (first time, or after they change)
uv run alembic upgrade head  # create or update all tables
```

Alembic connects as the owner role, using `MIGRATION_DATABASE_URL`. It applies these migrations in order:

| Migration | Creates |
|---|---|
| `0001_baseline` | the `citext` and `pg_trgm` extensions, and grants for `fintrack_app` |
| `0002_audit_log` | `audit_log`, which is append-only for the app role |
| `0003_users_and_auth_tokens` | `users`, `user_preferences`, `refresh_tokens`, `password_reset_tokens` |
| `0004_accounts_categories_ledger` | `accounts`, `categories`, `income_sources`, `transactions`, `salary_components`, `attachments`, `import_batches`, `idempotency_keys` |

To check that the tables exist, open psql (see [Connection details](#connection-details)) and run:

```sql
SELECT version_num FROM alembic_version;  -- should be 0004
\dt
```

Other migration commands (run them in `backend/`):

```bash
uv run alembic current          # show the applied revision
uv run alembic history          # list all revisions
uv run alembic downgrade base   # WARNING: drops every table and all data
```

Run `uv run alembic upgrade head` again whenever you pull new migrations.

## 5. Run the backend

The examples use port **5199** for the frontend, because ports 5173 and 5174 are already taken by other apps on this machine. If 5173 is free on your machine, you can drop the two variables in front of the command and run the frontend on its default port.

```bash
cd backend
CORS_ORIGINS=http://localhost:5199 FRONTEND_BASE_URL=http://localhost:5199 \
  uv run uvicorn app.main:app --reload --no-access-log
```

| URL | What it is |
|---|---|
| http://localhost:8000/api/docs | Swagger API docs (outside production only) |
| http://localhost:8000/health/live | Liveness check |
| http://localhost:8000/health/ready | Readiness check: confirms the database is reachable and migrations are up to date |

Keep `--no-access-log` in the command. Without it, uvicorn's access log prints full URLs, including search text and amount filters.

## 6. Run the frontend

```bash
cd frontend
npm ci                                 # install dependencies (first time, or after they change)
npm run dev -- --port 5199 --strictPort
```

Open **http://localhost:5199**. Vite forwards `/api` requests to the backend on port 8000. If the backend runs on a different port, set `VITE_API_PROXY`, for example `VITE_API_PROXY=http://localhost:8765`.

`--strictPort` makes Vite exit with an error if the port is busy. Without it, Vite quietly switches to another port, and the backend then rejects that port because it isn't in `CORS_ORIGINS`.

## 7. Password-reset email (optional)

```bash
mailpit
```

Mailpit receives mail on SMTP port 1025, which the backend's defaults already use. Read the emails at http://localhost:8025.

## 8. First use

1. Register an account at http://localhost:5199.
2. Add a money account (for example, a bank account) under **Settings → Accounts**.
3. Add transactions or income, then open the dashboard.

## Stopping everything

Press Ctrl+C in the backend, frontend and Mailpit terminals, then stop the database:

```bash
scripts/dev-db.sh stop
```

## Useful commands

| Task | Command |
|---|---|
| Backend tests (uses `fintrack_test`) | `cd backend && uv run pytest` |
| Backend lint and type check | `cd backend && uv run ruff check . && uv run mypy app` |
| Frontend tests | `cd frontend && npm test` |
| Frontend lint and type check | `cd frontend && npm run lint && npm run typecheck` |
| Production build of the frontend | `cd frontend && npm run build` |
| End-to-end tests (start their own servers on ports 8765 and 5199, so stop your frontend first) | `cd frontend && npx playwright test` |
| Regenerate the frontend API types after backend changes | `cd frontend && npm run gen:api` |

## Troubleshooting

| Symptom | Fix |
|---|---|
| `connection refused` on port 54329 | Start the database: `scripts/dev-db.sh start` |
| `/health/ready` reports that migrations are out of date | `cd backend && uv run alembic upgrade head` |
| Browser console shows CORS errors | The frontend is running on a port that isn't in `CORS_ORIGINS`. Make the two match. |
| `initdb: command not found` | Set `PGBIN` to your PostgreSQL `bin` directory. |
| Vite says the port is in use | Pick another free port, and update `CORS_ORIGINS` and `FRONTEND_BASE_URL` to match. |
