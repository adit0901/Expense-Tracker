# Proposal: FinTrack P0 – Core MVP

## Why

Individuals in India typically track income, spending, investments (Indian and US), loans and net worth across spreadsheets, bank apps and broker portals, with no single trustworthy view of their finances. FinTrack is a personal finance and wealth management platform that centralizes this view. P0 lays the secure, extensible foundation (repo, auth, data model, money handling) and delivers the first daily-use value: accurate income and expense tracking with a dashboard.

## Product Vision and Roadmap

FinTrack is delivered as a modular monolith (React + TypeScript frontend, FastAPI backend, PostgreSQL) in a single repository, through four sequential OpenSpec changes:

| Release | Change | Scope |
|---|---|---|
| **P0 – Core MVP** | `fintrack-p0-core-mvp` (this change) | Repo/platform setup, authentication, preferences, financial accounts, categories, income & expense transactions, dashboard, basic analytics |
| P1 – Financial Planning | `fintrack-p1-financial-planning` | Budgets, savings targets, goals, assets & liabilities, net worth, loans & EMIs |
| P2 – Wealth Management | `fintrack-p2-wealth-management` | Indian & US stock portfolios, investment transactions, market data, USD-INR conversion, portfolio analytics |
| P3 – Advanced Features | `fintrack-p3-advanced-features` | Recurring transactions, AI financial assistant, insights, advanced reports (CSV/PDF), notifications |

Changes must be implemented and archived in this order; later changes add requirements to capabilities introduced here. P0's design defines the whole-product architecture and full ER diagram so P1–P3 fit without redesign.

## What Changes

- Monorepo scaffold: `frontend/` (React, Vite, Tailwind, shadcn/ui, Recharts, TanStack Query, React Router), `backend/` (FastAPI, SQLAlchemy, Pydantic, Alembic, Pytest), `infrastructure/`, `docs/`, Docker Compose, `.env.example`, CI.
- Platform conventions: versioned REST API (`/api/v1`), consistent response envelope, pagination/filtering, error model, health checks, structured logging, OpenAPI docs.
- Security baseline: Argon2 password hashing, JWT access + rotating refresh tokens, per-user data isolation, rate limiting, input validation, safe uploads, log redaction, audit log of financial changes.
- User registration, login, logout, password reset, profile and preferences (INR default).
- Financial accounts (bank, cash, credit card, wallet) with derived balances.
- Default + custom categories and subcategories, with an "essential" flag used later for emergency-fund calculations.
- Transactions with explicit types (income, expense, transfer, …), payment methods, search/filter, CSV import/export, receipt attachments, duplicate detection.
- Income sources with salary breakdown (gross, deductions, net).
- Centralized, Decimal-based financial calculations (savings, savings rate, category totals).
- Overview dashboard (income, expenses, savings, savings rate, charts, date filters) and basic analytics.
- App shell with full 12-section navigation (unreleased sections show a "coming in a later release" state), light/dark theme and design system.

## Capabilities

### New Capabilities
- `platform-foundation`: API versioning, response/error envelope, pagination, health checks, structured logging, configuration.
- `security-baseline`: data isolation, rate limiting, input validation, upload safety, log redaction, audit logging.
- `user-auth`: registration, login, logout, token refresh, password reset.
- `user-profile`: profile details and preferences (currency, theme, locale, date format).
- `financial-accounts`: user-owned money accounts and their balances.
- `transaction-categories`: default and custom categories/subcategories.
- `transactions`: recording, classifying, searching, importing/exporting money movements, receipts, duplicate detection.
- `income-management`: income sources and salary breakdowns, income reports.
- `financial-calculations`: authoritative formulas and accounting rules (what counts as income/expense, Decimal arithmetic, edge cases).
- `dashboard-overview`: overview KPIs, charts and date filters.
- `app-shell-ui`: navigation, layout, theming, and shared UI states.

### Modified Capabilities
- None (no existing specs).

## Impact

- New codebase: everything under `frontend/`, `backend/`, `infrastructure/`, `docs/`, plus root `docker-compose.yml`, `.env.example`, `.gitignore`, `README.md`.
- New runtime dependencies: PostgreSQL 16, Mailpit (dev email). Redis is deferred to P1.
- The repository is not yet a Git repository; P0 initializes it.

## Decisions Requiring Approval

1. **Repository root** is the current `Expense-Tracker` directory (not a nested `fintrack/`). The folder name has a leading space (`/ Expense-Tracker`), which breaks some Docker/shell tooling; renaming it to `fintrack` is recommended before implementation.
2. **Reporting currency fixed to INR** in P0–P3. The preferred-currency preference is stored and displayed but other reporting currencies are out of scope.
3. **"EMIs" is not an expense category.** Loan payments become a dedicated transaction type (introduced in P1) so only interest counts as an expense; the default category list replaces "EMIs" with "Loan Interest" (system-managed).
4. **Auth tokens**: short-lived access JWT held in memory; refresh token in an httpOnly, Secure, SameSite=Strict cookie, rotated on use.
5. **Receipts** are stored on a local volume behind a storage interface (S3-compatible storage later).
6. **Credit card purchases count as expenses on the purchase date**; paying the card bill is a transfer, never an expense.

## Out of Scope (P0)

Budgets, goals, net worth, assets/liabilities, loans, investments, market data, FX, recurring transactions, AI assistant, PDF reports, notifications, multi-currency reporting, bank/SMS auto-sync, mobile apps, multi-user households.
