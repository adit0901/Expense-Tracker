# Tasks: FinTrack P0 – Core MVP

## 1. Repository and tooling scaffold

- [x] 1.1 Confirm the repo folder rename decision (leading-space path), run `git init`, add root `.gitignore`, `README.md` skeleton and `.env.example`; verify `git status` shows only intended files and no secrets
- [x] 1.2 Scaffold `backend/` (uv project, FastAPI, SQLAlchemy 2, Pydantic v2, Alembic, structlog, argon2-cffi, PyJWT, slowapi, pytest, ruff, mypy) with the D1 package layout; verify `uv run pytest` (empty suite) and `ruff check` pass
- [x] 1.3 Scaffold `frontend/` (Vite React TS strict, Tailwind, shadcn/ui init, Recharts, TanStack Query, React Router, React Hook Form, Zod, Vitest, RTL, MSW, ESLint) with the D12 folder layout; verify `npm run build`, `npm run lint` and `npm test` pass
- [ ] 1.4 Add `docker-compose.yml` (postgres:16, mailpit, backend, frontend) and Dockerfiles in `infrastructure/`; verify `docker compose up` serves the Vite page and backend `/health/live` returns 200
- [ ] 1.5 Add GitHub Actions CI (backend lint/type/test with Postgres service, frontend lint/type/test/build); verify a pushed branch runs green

## 2. Platform foundation (backend core)

- [x] 2.1 Implement settings loader with production guard for missing/default secrets; verify a unit test that startup fails with `APP_ENV=production` and default JWT key
- [x] 2.2 Implement DB session management, Alembic baseline with `citext` and `pg_trgm` extensions; verify `alembic upgrade head` and `downgrade base` succeed in CI
- [x] 2.3 Implement response envelope, error envelope, domain exception handlers and 422 validation mapping; verify integration tests for 422 `details` and 500 without internals
- [x] 2.4 Implement pagination/sort helpers with page-size cap and sort allow-lists; verify tests for `page_size=500` and disallowed sort field
- [x] 2.5 Implement Decimal context, money types and string serialization; verify tests that 0.10+0.20+0.30 = 0.60 and amounts serialize as strings
- [x] 2.6 Implement request-id middleware and structlog JSON logging with redaction processor; verify a test asserting `X-Request-ID` header and that a logged payload with `password`/`amount` keys is redacted
- [x] 2.7 Implement `/health/live` and `/health/ready` (DB + migration head check); verify 503 when DB is unavailable in a test
- [x] 2.8 Add security headers, CORS allow-list and OpenAPI at `/api/docs` (non-prod only); verify tests for CORS rejection and docs disabled in production
- [x] 2.9 Implement audit-log model and service with no update/delete path, and a DB role grant restricting UPDATE/DELETE; verify a test that audit rows are created and cannot be modified
- [x] 2.10 Write `docs/architecture.md` (layers, module rules, API conventions); verify it matches the implemented envelope and pagination by linking the relevant tests

## 3. Authentication and users

- [x] 3.1 Create `users`, `user_preferences`, `refresh_tokens`, `password_reset_tokens` models and migration; verify migration up/down
- [x] 3.2 Implement registration (Argon2id, case-insensitive unique email, password policy with common-password list, default preferences); verify tests for success, `email_taken` and weak password
- [x] 3.3 Implement login, access JWT, refresh cookie, rotation with reuse detection and logout; verify tests for valid login, identical `invalid_credentials`, rotation, reuse revoking the family, and logout
- [x] 3.4 Implement login rate limiting per IP and per email; verify the sixth failed attempt returns 429 with `Retry-After`
- [x] 3.5 Implement password reset request/confirm with Mailpit SMTP adapter, hashed single-use 30-min tokens and session revocation; verify tests for unknown email (same 202), success, expiry
- [x] 3.6 Implement change password, profile read/update (email change requires password) and preferences (INR-only currency); verify tests including `unsupported_currency`
- [x] 3.7 Implement account deletion (password confirmation, cascade delete of data and files, audit anonymization); verify a test that no records remain retrievable
- [x] 3.8 Implement the authenticated-user dependency and cross-tenant test harness (second user fixture + parametrized endpoint sweep); verify it runs against all auth/user endpoints

## 4. Accounts and categories

- [x] 4.1 Create `accounts` model/migration and CRUD + archive endpoints with last-4 validation; verify tests including `account_has_transactions` 409 and archive behavior
- [x] 4.2 Create `categories` model/migration; seed default income/expense categories (incl. system "Loan Interest" and essential flags) on registration; verify a test of a new user's categories
- [x] 4.3 Implement custom categories/subcategories (one level, case-insensitive uniqueness), essential toggle, delete-with-replacement and system-category protection; verify tests for third-level rejection, `category_in_use`, reassignment
- [x] 4.4 Add accounts and categories to the cross-tenant sweep and audit assertions; verify the sweep passes

## 5. Transactions core

- [x] 5.1 Create `transactions`, `salary_components`, `attachments`, `import_batches` models with DB CHECK constraints and indexes per D8; verify migration and constraint tests (e.g. transfer with category rejected)
- [x] 5.2 Implement `signed_effect` sign rules and derived account balance queries (bank, cash, wallet, credit card outstanding); verify table-driven unit tests and the accounts summary scenario (liquid 120000.00, card 5000.00)
- [x] 5.3 Implement create/read/update/delete for income, expense, transfer and refund with kind/payment-method/account validation; verify tests for each spec scenario (card bill transfer, same-account transfer, mismatch errors, decimals)
- [x] 5.4 Implement search/filter/sort (date range, type, account, category incl. subcategories, method, amount range, tag, text via trigram); verify tests including the Food-in-October scenario and SQL meta-character search
- [x] 5.5 Implement duplicate detection (D9) on create with `confirm_duplicate` and the duplicate-check endpoint; verify tests for warning and confirmed save
- [x] 5.6 Implement idempotency-key handling on transaction POST; verify a retried request with the same key creates one transaction
- [x] 5.7 Implement storage backend and receipt attachments (sniffed type allow-list, 10 MB limit, max 5, owner-only download, cascade delete); verify tests for disguised executable, 413, and cross-tenant download 404
- [x] 5.8 Implement CSV export with formula-injection escaping; verify a test with `=HYPERLINK` description
- [x] 5.9 Implement CSV import (upload, encoding detection, mapping, preview with errors and duplicate flags, atomic confirm, 24 h undo); verify tests for invalid-date row, atomic rollback on failure, undo
- [x] 5.10 Add transactions, attachments and imports to the cross-tenant sweep and audit assertions; verify the sweep passes

## 6. Income management and calculations

- [x] 6.1 Implement income sources CRUD/deactivate; verify tests for multiple sources
- [x] 6.2 Implement salary breakdown validation (net = gross − deductions = credited amount); verify tests for valid breakdown and `salary_breakdown_mismatch`
- [x] 6.3 Implement `services/calculations` for period resolution (month, quarter, calendar year, FY, custom; Asia/Kolkata), monthly income, expenses net of refunds, savings, savings rate (null on zero income), category totals and shares; verify table-driven unit tests for every scenario in `financial-calculations` with ≥ 90% coverage
- [x] 6.4 Implement income report endpoint (monthly, per source, salary gross/deductions/net) and CSV export; verify integration test for the annual report scenario
- [x] 6.5 Write `docs/financial-calculations.md` with each formula and worked examples mirrored by tests; verify each example has a matching test id referenced in the doc

## 7. Dashboard and analytics APIs

- [x] 7.1 Implement `/dashboard/overview` (KPI tiles with previous-period change, "—" for zero base) ; verify tests for November vs October and zero-base change
- [x] 7.2 Implement `/dashboard/trends` (12 months incl. zero months, savings rate gaps) and `/dashboard/category-breakdown` (top 6 + other); verify tests for 18-month data and gap months
- [x] 7.3 Implement expense report by category and payment method, savings-trend report and CSV exports; verify payment-method totals sum to total expenses
- [x] 7.4 Verify dashboard and report endpoints return identical figures for the same period in an integration test

## 8. Frontend shell and auth

- [x] 8.1 Build design tokens (light/dark CSS variables), theme provider applied before first paint, and base shadcn components; verify a Vitest test that theme preference toggles the root class and a manual contrast check in both themes
- [x] 8.2 Generate API types from OpenAPI and build the API client with in-memory token and single-flight refresh on 401; verify Vitest tests with MSW for refresh success and refresh failure redirect
- [x] 8.3 Build register, login, forgot/reset password and change-password pages with inline validation; verify RTL tests for error display and preserved input
- [x] 8.4 Build the protected app layout with full navigation, mobile drawer under 1024 px, and coming-soon pages for unreleased sections; verify RTL tests that coming-soon pages make no API calls and a 375 px viewport check in Playwright
- [x] 8.5 Build Settings (profile, preferences incl. number grouping, account deletion with confirmation); verify RTL tests and the Indian grouping formatter test (`₹12,34,567.89`)

## 9. Frontend features

- [x] 9.1 Build Accounts management UI (create/edit/archive, balances, summary); verify RTL tests for create and archive confirmation
- [x] 9.2 Build Categories management UI (subcategories, essential toggle, delete with replacement); verify RTL tests for replacement flow
- [x] 9.3 Build Transactions list with filters, search, pagination, and drill-down query params; verify RTL tests that filters map to query params
- [x] 9.4 Build transaction form (type-dependent fields, transfer, refund, salary breakdown, duplicate warning confirm) and delete confirmation; verify RTL tests for duplicate confirm and breakdown mismatch error
- [x] 9.5 Build receipt upload/view/delete and CSV export button; verify RTL tests for upload error messages
- [x] 9.6 Build CSV import wizard (upload, mapping, preview with errors/duplicates, confirm, undo); verify RTL tests for preview rendering and deselected duplicates
- [x] 9.7 Build Income and Expenses pages (source/category breakdowns) and Reports & Analytics P0 views with CSV export; verify RTL tests with MSW fixtures
- [x] 9.8 Build Overview dashboard (KPI tiles, period filter incl. custom and FY, income vs expense, savings trend, category donut with drill-down, recent transactions, skeleton/empty/error states, chart table alternatives); verify RTL tests for empty state and drill-down navigation

## 10. Integration verification

- [ ] 10.1 Write Playwright E2E: register → create account → add salary with breakdown and expenses → dashboard shows expected income, expenses, savings, savings rate; verify it passes against `docker compose`
- [ ] 10.2 Write Playwright E2E for CSV import with a duplicate row and for password reset via the Mailpit API; verify both pass
- [x] 10.3 Run the full cross-tenant sweep, a log-redaction check over E2E logs (no amounts, descriptions or tokens), and the accessibility check (axe) on main pages; verify zero violations of severity serious or higher
- [x] 10.4 Complete README (setup, env vars, commands) and `docs/runbook.md`; verify a fresh clone reaches a working app by following the README only

## Workflow follow-up

- Archive this change after review, before starting `fintrack-p1-financial-planning`, so its specs become the baseline for P1 deltas.
