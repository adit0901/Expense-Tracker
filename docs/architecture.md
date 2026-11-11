# FinTrack architecture

FinTrack is a modular monolith: a React + TypeScript SPA (`frontend/`) talking to a FastAPI
backend (`backend/`) over a versioned JSON API, with PostgreSQL as the only stateful dependency
in P0. The full design rationale lives in
`openspec/changes/fintrack-p0-core-mvp/design.md`; this document describes the rules the code
follows.

## Backend layers

```
HTTP request
  └─ app/api/v1/<domain>.py      routers: parse input, resolve the current user, call a service,
                                 wrap the result in the response envelope. No SQL, no business rules.
      └─ app/services/<domain>/   business rules, DB transaction boundaries (commit), audit entries.
          ├─ app/services/calculations/   pure functions over Decimals/dataclasses. No DB, no I/O.
          └─ app/repositories/            query objects, always constructed with a user_id and
                                          adding it to every query.
              └─ app/models/              SQLAlchemy ORM models.
app/schemas/       Pydantic request/response models.
app/core/          config, db session, errors, logging, middleware, money, pagination, security.
app/integrations/  adapters behind Protocols (storage, email; later market data, FX, LLM).
```

Module rules:

1. Routers never touch the ORM directly; services never import FastAPI.
2. Financial math lives only in `services/calculations` so every figure has one implementation
   that the dashboard, reports, exports and (P3) the assistant all reuse.
3. A domain may call another domain's **service**, never its repository.
4. Every user-owned table has `user_id NOT NULL`; repositories require it. Requests for another
   user's resource return 404.
5. Services that change financial records call `app.services.audit.record(...)` inside the same
   DB transaction. `audit_log` is append-only: the application DB role (`fintrack_app`) has no
   UPDATE/DELETE/TRUNCATE privilege on it; migrations run as the owner role (`fintrack`).

## API conventions

| Concern | Convention | Implementation | Verified by |
|---|---|---|---|
| Versioning | All business endpoints under `/api/v1/<domain>`; unversioned paths 404 | `app/api/v1/__init__.py` | `tests/unit/test_api_conventions.py::test_unversioned_path_is_404` |
| Success envelope | `{"data": ..., "meta": {...}}` | `app/core/responses.py` | `test_api_conventions.py::test_success_envelope_and_string_amount` |
| Error envelope | `{"error": {"code", "message", "details", "request_id"}}` | `app/core/errors.py` | `test_api_conventions.py::test_validation_error_lists_field`, `::test_unhandled_error_hides_internals` |
| Validation | HTTP 422, `code=validation_error`, one `details` entry per field (`field`, `message`, `type`) | `app/core/errors.py` | `test_api_conventions.py::test_validation_error_lists_field` |
| Pagination | `page` (≥1), `page_size` (default 25, max 100); `meta.page/page_size/total_items/total_pages` | `app/core/pagination.py` | `test_api_conventions.py::test_page_size_capped_at_100`, `::test_allowed_sort_and_meta` |
| Sorting | `sort=-date,amount`; per-endpoint allow-list; otherwise 422 `invalid_sort` | `app/core/pagination.py::parse_sort` | `test_api_conventions.py::test_disallowed_sort_field` |
| Money | Decimal end to end; serialized as strings (`"1250.50"`) with a `currency` code; final figures round half-up to 2 dp | `app/core/money.py` | `tests/unit/test_money.py` |
| Request id | `X-Request-ID` echoed or generated; present in every log line and error body | `app/core/middleware.py` | `tests/unit/test_logging.py::test_request_log_line_matches_header` |
| Logging | One JSON line per request (request id, method, route template, status, duration, user id); sensitive keys redacted | `app/core/logging.py` | `test_logging.py::test_logged_payload_is_redacted_in_output` |
| Health | `GET /health/live`, `GET /health/ready` (DB + Alembic head), 503 naming the failing dependency | `app/api/health.py` | `tests/integration/test_health.py` |
| Security headers / CORS | HSTS, CSP, nosniff, frame denial; CORS limited to `CORS_ORIGINS` | `app/core/middleware.py`, `app/main.py` | `test_api_conventions.py::test_security_headers_and_request_id`, `::test_cors_rejects_unknown_origin` |
| API docs | OpenAPI at `/api/openapi.json`, Swagger UI at `/api/docs`; disabled in production | `app/main.py` | `tests/unit/test_config.py::test_production_with_valid_secrets_starts_and_hides_docs` |
| Idempotency | `Idempotency-Key` header accepted on transaction and import POSTs | task 5.6 | — |

## Configuration

Settings come only from environment variables (see `.env.example`), loaded by
`app/core/config.py`. With `APP_ENV=production` the app refuses to start when `JWT_SECRET` is
missing, the development default, or shorter than 32 characters, or when `DATABASE_URL` is not
set explicitly.

## Database

- PostgreSQL 16+ with `citext` and `pg_trgm`, created by the baseline migration.
- Two roles: `fintrack` owns the schema and runs Alembic (`MIGRATION_DATABASE_URL`);
  `fintrack_app` is used by the running API (`DATABASE_URL`) and gets DML privileges through
  default privileges set in migration `0001`.
- Money columns are `NUMERIC(19,4)` with a sibling `currency CHAR(3)`.
- Migrations are forward-only in deployment, but every revision has a working downgrade; CI runs
  upgrade → downgrade base → upgrade.

## Frontend

See design decision D12: Vite + React + TS strict, React Router with a protected layout,
TanStack Query for server state, React Hook Form + Zod, shadcn/ui on Tailwind CSS variables for
light/dark themes, Recharts wrapped in `components/charts` with table fallbacks. The browser never
computes financial totals; it only formats strings it receives.
