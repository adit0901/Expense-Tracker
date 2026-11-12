# FinTrack

Personal finance tracking for India-based users. FinTrack records income and expenses
across bank accounts, cash, credit cards and wallets, and reports savings and savings rate.
Reporting is in INR, and all money arithmetic is exact (decimal, never floating point).

It is built as a modular monolith:

- a React and TypeScript single-page app (`frontend/`)
- a FastAPI API (`backend/`)
- PostgreSQL as the database.

**Status: P0 (Core MVP).** P0 covers:

- authentication
- preferences
- money accounts
- categories
- income and expense transactions, with CSV import and export and receipts
- income sources with salary breakdowns
- the Overview dashboard and basic reports.

Budgets, goals, net worth, loans, investments and the AI assistant arrive in later releases.
They appear in the navigation as "Coming in a later release". The roadmap and specs are in
`openspec/changes/`.

## Repository layout

```
frontend/        React 19 + Vite + Tailwind + shadcn/ui, TanStack Query, React Router, Recharts
backend/         FastAPI + SQLAlchemy 2 + Alembic (app/, alembic/, tests/, scripts/)
infrastructure/  Dockerfiles, nginx config, database init SQL
docs/            architecture.md, financial-calculations.md, runbook.md
scripts/         dev-db.sh: a local PostgreSQL cluster without Docker
openspec/        Specifications and change proposals
```

## Prerequisites

You need **one** of these two setups.

| Setup | You need |
|---|---|
| **A. Docker** | Docker Desktop, OrbStack or another Docker Engine with Compose v2 |
| **B. Local** | Python 3.13 with [uv](https://docs.astral.sh/uv/) 0.10 or later, Node.js 24 with npm, PostgreSQL 16 or later server binaries (`initdb`, `pg_ctl`, `psql`), and optionally [Mailpit](https://mailpit.axllent.org/) for password-reset email |

## Quick start A: Docker

```bash
cp .env.example .env              # optional; compose reads .env.example by default
docker compose up --build
```

| Service | URL |
|---|---|
| App (Vite dev server) | http://localhost:5173 |
| API docs (Swagger) | http://localhost:8000/api/docs |
| Health | http://localhost:8000/health/ready |
| Mailpit (dev email) | http://localhost:8025 |

The backend runs `alembic upgrade head` on start. To try a production-style build, run
`docker compose --profile prod up --build`. It serves the built frontend from nginx on
http://localhost:8080 and proxies `/api` to the backend.

## Quick start B: local, without Docker

Run each long-running command in its own terminal, starting from the repository root.
For a fuller walkthrough, with connection strings, the list of tables and troubleshooting
tips, see [docs/running-locally.md](docs/running-locally.md).

**1. Start PostgreSQL.** This creates a cluster in `.local/pgdata` on port 54329, with the
roles `fintrack` (owner) and `fintrack_app` (application) and the databases `fintrack` and
`fintrack_test`:

```bash
scripts/dev-db.sh start
```

If your PostgreSQL binaries aren't in `/Library/PostgreSQL/18/bin`, set `PGBIN`. For example,
with Homebrew:

```bash
PGBIN=/opt/homebrew/opt/postgresql@16/bin scripts/dev-db.sh start
```

**2. Start the API.** The defaults already point at the local cluster from step 1.

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --no-access-log
```

**3. Start Mailpit (optional).** Password-reset emails appear at http://localhost:8025.

```bash
mailpit
```

**4. Start the web app.** Vite proxies `/api` to http://localhost:8000.

```bash
cd frontend
npm ci
npm run dev
```

Open the URL Vite prints (normally http://localhost:5173), create an account, add a money
account under **Settings → Accounts**, then add transactions.

To use other ports, set `VITE_API_PROXY` for the web app (for example
`VITE_API_PROXY=http://localhost:8765 npm run dev -- --port 5199`). Set the matching
`FRONTEND_BASE_URL` for the API so reset links point at the right address.

To stop or reset the database, run `scripts/dev-db.sh stop` or `scripts/dev-db.sh reset`.
`reset` deletes all local data.

## Configuration

All settings come from environment variables; see `.env.example`. The backend also reads a
`.env` file from its working directory (`backend/.env`).

| Variable | Default (development) | Purpose |
|---|---|---|
| `APP_ENV` | `development` | `development`, `test` or `production`. Production refuses default secrets and hides `/api/docs`. |
| `DATABASE_URL` | `postgresql+psycopg://fintrack_app:fintrack_app@localhost:54329/fintrack` | API connection, using the application role |
| `MIGRATION_DATABASE_URL` | `postgresql+psycopg://fintrack:fintrack@localhost:54329/fintrack` | Alembic connection, using the owner role |
| `JWT_SECRET` | `change-me-dev-secret` | Access-token signing key. Must be at least 32 random characters in production. |
| `ACCESS_TOKEN_TTL_MINUTES` / `REFRESH_TOKEN_TTL_DAYS` | `15` / `7` | Session lifetimes |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed browser origins (comma-separated) |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_FROM` | `localhost` / `1025` / `FinTrack <no-reply@fintrack.local>` | Outgoing email |
| `FRONTEND_BASE_URL` | `http://localhost:5173` | Used to build password-reset links |
| `UPLOAD_DIR` | `./data/uploads` | Receipt storage (keep it outside any web root) |
| `API_RATE_LIMIT` | `300/minute` | Per-user API limit. Failed logins are limited separately (5 per 15 minutes per IP and per email). |

## Development commands

| Task | Backend (`cd backend`) | Frontend (`cd frontend`) |
|---|---|---|
| Lint | `uv run ruff check . && uv run ruff format --check .` | `npm run lint` |
| Type-check | `uv run mypy` | `npm run typecheck` |
| Unit and integration tests | `uv run pytest --cov=app` (needs the dev database running) | `npm test` |
| Migrations | `uv run alembic upgrade head` / `uv run alembic downgrade -1` | n/a |
| New migration | `uv run alembic revision --autogenerate -m "..."` | n/a |
| API types | n/a | `npm run gen:api` (regenerates `src/types/api.d.ts` from the backend) |
| Production build | n/a | `npm run build` |
| End-to-end | n/a | `npx playwright install chromium`, then `npm run e2e` |

Backend tests use the `fintrack_test` database and reset its schema at the start of each run.

The end-to-end suite needs the dev database (`scripts/dev-db.sh start`) and the `mailpit`
binary. It starts its own API (port 8765), web app (port 5199) and Mailpit, so it never
attaches to other servers you have running. To run it against an already running stack
instead, use `E2E_EXTERNAL=1 BASE_URL=http://localhost:5173 npm run e2e`.

## Documentation

- [docs/architecture.md](docs/architecture.md): layers, module rules and API conventions
- [docs/financial-calculations.md](docs/financial-calculations.md): every formula, with
  worked examples linked to tests
- [docs/runbook.md](docs/runbook.md): operating, deploying and troubleshooting
- API reference: `/api/docs` when not in production (OpenAPI JSON at `/api/openapi.json`)
