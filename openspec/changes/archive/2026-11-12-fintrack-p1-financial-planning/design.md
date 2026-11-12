# Design: FinTrack P1 – Financial Planning

## Context

Builds on the architecture, layering, money types and ER diagram in `fintrack-p0-core-mvp/design.md` (assumed implemented and archived). See proposal.md for scope and the specs in this change for requirements. P0 has no background jobs and uses in-memory rate limiting.

## Goals / Non-Goals

**Goals:**
- Deterministic, unit-tested EMI/amortization and net worth engines in `services/calculations`.
- Loan payments that keep the ledger, loan outstanding and expense totals consistent in one DB transaction.
- Scheduled jobs that are idempotent and safe to re-run.

**Non-Goals:**
- Lender statement import, day-count conventions other than monthly (30/360-equivalent monthly rate), daily-reducing interest, moratorium modeling.
- Email/push alerts (P3 notifications deliver P1 alerts to other channels).

## Decisions

### D1. New tables (extending P0 ER diagram)
| Table | Key columns |
|---|---|
| `budgets` | `user_id`, `month DATE` (first of month), `overall_amount NULL`; unique (`user_id`,`month`) |
| `budget_lines` | `budget_id`, `category_id`, `amount`, `alert_thresholds INT[]` default `{80,100}`; unique (`budget_id`,`category_id`) |
| `budget_alerts` | `user_id`, `budget_line_id NULL` (NULL = overall), `month`, `threshold`, `triggered_at`; unique (`budget_line_id`,`month`,`threshold`) — guarantees one alert per threshold per month |
| `savings_targets` | `user_id`, `effective_from DATE`, `amount` |
| `goals` / `goal_contributions` | goal fields per spec; contributions `kind` (`contribution`/`withdrawal`), `amount`, `date`, `transaction_id NULL` |
| `assets` / `asset_valuations` | `type` enum, `name`, `details JSONB` (validated per type by Pydantic discriminated union), `is_liquid`, `closed_at`; valuations (`asset_id`,`as_of`,`value`) unique per date |
| `liabilities` / `liability_balances` | same pattern for other debts |
| `loans` | `type`, `lender`, `original_principal`, `annual_rate`, `tenure_months`, `start_date`, `first_emi_date`, `emi_amount`, `emi_overridden`, `baseline_outstanding`, `baseline_date`, `status` |
| `loan_events` | `loan_id`, `kind` (`rate_change`,`prepayment`,`emi_override`), `effective_date`, `payload JSONB` — schedule is regenerated from baseline + events |
| `loan_payments` | `loan_id`, `installment_no NULL`, `transaction_id UNIQUE`, `principal`, `interest` |
| `net_worth_snapshots` | `user_id`, `as_of DATE`, `total_assets`, `total_liabilities`, `net_worth`, `breakdown JSONB`, `computed_at`, `is_stale`; unique (`user_id`,`as_of`) |

`transactions` gains `loan_id NULL`, `principal_component NULL`, `interest_component NULL`, CHECK for `loan_payment` ⇒ components sum to amount. Expense aggregation query becomes `expense − refund + interest_component(loan_payment)`.

### D2. Loan schedule is computed, not stored as source of truth
The schedule is a pure function `build_schedule(baseline, events, payments)` returning installments; it is computed on read (≤ 360 rows, cheap) and cached per loan version. *Alternative*: persist schedule rows and mutate on events — rejected, error-prone when prepayments/rate changes interleave. Actual payments are stored separately; outstanding principal = baseline − Σ principal components after baseline date. The schedule's "expected" outstanding is shown alongside actual when they diverge (missed or partial payments).

### D3. Interest convention
Monthly rate r = annual ÷ 1200 using Decimal; interest per installment rounded half-up to 2 dp; EMI computed with full precision then rounded; final installment = remaining principal + its interest. Rate changes and prepayments recompute from the effective date's outstanding with the chosen keep-EMI/keep-tenure option; "keep EMI" is rejected when EMI ≤ interest (negative amortization).

### D4. Loan payment flow
`POST /loans/{id}/payments` (confirm installment or record custom/prepayment) runs in one DB transaction: compute split from the current schedule (or user-provided split for custom payments, validated to sum), insert `transactions` row (`loan_payment`), insert `loan_payments`, write audit entries. The generic `POST /transactions` rejects `loan_payment`.

### D5. Net worth engine
`compute_net_worth(user, as_of)` aggregates: account balances as of date (P0 derived balances with date bound), latest asset/liability valuations ≤ as_of excluding closed, loan outstanding as of date, card outstanding; (P2 hook) `investment_value_provider(user, as_of)` returning INR value — a registered no-op in P1 so P2 plugs in without changing the engine. Snapshots persist results; editing any dated financial record older than the latest snapshot marks affected snapshots `is_stale` (via service-layer hook), shown in UI with "Recompute".

### D6. Background jobs: Redis + ARQ
Add Redis and an ARQ worker (async, lightweight, fits FastAPI). Cron jobs: month-end snapshots (runs daily at 00:30 IST, snapshots any missing month-end for each user — idempotent via unique key), budget alert evaluation also happens synchronously on transaction writes (immediate UX) with the unique constraint preventing duplicates. Rate-limit storage moves to Redis. *Alternative*: Celery + beat — heavier; APScheduler in-process — breaks with multiple API replicas.

### D7. API additions
`/budgets?month=`, `PUT /budgets/{month}`, `POST /budgets/{month}/copy-from/{source_month}`, `/budgets/comparison`, `/budget-alerts`; `/savings-targets`, `/goals`, `/goals/{id}/contributions`; `/assets`, `/assets/{id}/valuations`, `/liabilities`, `/liabilities/{id}/balances`; `/loans`, `/loans/{id}/schedule`, `/loans/{id}/payments`, `/loans/{id}/events`, `POST /loans/{id}/simulate`, `/loans/summary`; `/net-worth?as_of=`, `/net-worth/snapshots`, `POST /net-worth/snapshots`, `POST /net-worth/snapshots/{as_of}/recompute`; `/dashboard/overview` extended; `GET /metrics/emergency-fund`.

### D8. Frontend
Feature folders `budgets`, `goals`, `networth`, `loans`, `assets`. Loan detail page with schedule table (virtualized), payment confirm dialog showing split, simulation drawer comparing current vs simulated (chart + table). Loans & EMIs sub-navigation filters by type (Home, Car, Other).

## Risks / Trade-offs

- [Users' lender schedules differ by a few rupees] → EMI override and custom payment split; display divergence instead of forcing.
- [Computed schedules with many events] → cache by loan version; property-based tests ensure closing balance 0 and principal sum = P.
- [Stale snapshots confuse users] → explicit stale badge and recompute; never silently rewrite history.
- [Worker downtime misses month-end] → job backfills any missing month-end snapshots on next run (computing as of that date from dated data).
- [Mutual funds manual in P1 then automated in P2] → P2 migration offers converting manual MF assets to holdings; until then no double counting because each lives in one place.

## Migration Plan

Forward Alembic migrations for new tables and new `transactions` columns/enum value (`ALTER TYPE … ADD VALUE` in its own migration). Deploy Redis and worker before enabling cron. Rollback: disable worker, downgrade migrations (loan_payment rows must be removed first; downgrade script refuses if any exist).

## Open Questions

- Should goal contributions optionally auto-create the transfer transaction? (UI convenience; does not change specs.)
