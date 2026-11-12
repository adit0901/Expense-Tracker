# Tasks: FinTrack P1 – Financial Planning

## 1. Infrastructure

- [x] 1.1 Add Redis and ARQ worker services to Docker Compose and CI; verify `docker compose up` starts the worker and a health job runs
- [x] 1.2 Move rate-limit storage to Redis; verify the P0 login rate-limit test passes against Redis

## 2. Calculations engine

- [x] 2.1 Implement EMI and amortization (`build_schedule`) incl. zero-rate and final-installment adjustment; verify table-driven tests for the spec examples (88848.79 / 88848.76 / 66185.45; 8333.33 ×11 + 8333.37; 43391.16) and property tests (closing 0.00, Σ principal = P)
- [x] 2.2 Implement prepayment, rate change (keep EMI/keep tenure, negative-amortization rejection) and simulation functions; verify unit tests for reduce-tenure and rate-hike scenarios
- [x] 2.3 Implement budget utilization, savings-target achievement, goal projections (required monthly contribution, 3-month average ETA, overdue) and emergency-fund coverage; verify unit tests incl. null cases
- [x] 2.4 Implement `compute_net_worth` with the investment-value hook (no-op), overdraft as liability, closed items excluded; verify unit tests for the spec's -4155000.00 example and overdraft scenario
- [x] 2.5 Extend `docs/financial-calculations.md` with EMI, amortization, net worth, budget, goal and emergency-fund formulas and worked examples; verify each example maps to a test

## 3. Budgets

- [x] 3.1 Create `budgets`, `budget_lines`, `budget_alerts` migrations and endpoints (set, get, copy-forward, comparison) with roll-up and over-allocation warning; verify integration tests for each spec scenario
- [x] 3.2 Evaluate alert thresholds on transaction create/update/delete with unique-per-month alerts; verify tests for single 80% alert and no duplicates after delete/re-cross
- [x] 3.3 Add budgets to cross-tenant sweep and audit; verify sweep passes

## 4. Savings targets and goals

- [x] 4.1 Create `savings_targets`, `goals`, `goal_contributions` migrations and endpoints; verify tests for achievement (120.00, negative savings) and over-withdrawal 422
- [x] 4.2 Expose goal progress and projections in API responses labeled as estimates; verify tests for required contribution 25000.00, "Cannot estimate" and overdue
- [x] 4.3 Add to cross-tenant sweep and audit; verify sweep passes

## 5. Assets and liabilities

- [x] 5.1 Create `assets`, `asset_valuations`, `liabilities`, `liability_balances` migrations, per-type detail validation and endpoints; verify tests for FD creation, rejected `bank` type and historical valuation lookup
- [x] 5.2 Implement closing with history retention; verify the sold-property scenario test
- [x] 5.3 Add to cross-tenant sweep and audit; verify sweep passes

## 6. Loans and EMIs

- [x] 6.1 Create `loans`, `loan_events`, `loan_payments` migrations and `transactions` columns/enum value `loan_payment` with CHECK; verify migration up/down and constraint tests
- [x] 6.2 Implement loan CRUD incl. mid-tenure baseline and EMI override; verify tests for new home loan and existing loan scenarios
- [x] 6.3 Implement schedule endpoint (cached per loan version) and loan summaries (paid to date, remaining interest, total EMI commitment); verify the 55891.16 commitment test
- [x] 6.4 Implement confirmed EMI payment and prepayment flow (atomic transaction + loan_payment + audit), block `loan_payment` on generic endpoint, and update expense aggregation to include only interest; verify tests: bank −88848.79, outstanding 921151.21, expenses +10000.00; prepayment not an expense
- [x] 6.5 Implement rate change events and simulation endpoint (no persistence); verify tests that simulation leaves the loan unchanged
- [x] 6.6 Add loans to cross-tenant sweep and audit; verify sweep passes

## 7. Net worth

- [x] 7.1 Create `net_worth_snapshots` migration and endpoints (current, history, on-demand, recompute); verify tests for breakdown shares summing to 100%
- [x] 7.2 Implement month-end snapshot cron with backfill and idempotency, and stale marking on back-dated edits; verify tests for 2026-11-30 snapshot, rerun creating no duplicates, stale flag after October edit
- [x] 7.3 Implement MoM/YoY growth with null and negative-base rules; verify tests for 5.00% MoM and missing YoY "—"

## 8. Dashboard extension

- [x] 8.1 Extend `/dashboard/overview` with net worth, assets, liabilities, loans, EMI commitment, savings target, budget status, and add net worth/asset allocation/loan trend series; verify integration tests incl. "Set a target" state

## 9. Frontend

- [x] 9.1 Build Budgets page (month picker, overall and category budgets, utilization bars, over-budget state, copy forward, comparison chart, alerts list); verify RTL tests with MSW
- [x] 9.2 Build Savings & Goals page (target vs actual, goal cards, contribution dialog, projection labels); verify RTL tests for estimate labels and overdue state
- [x] 9.3 Build Net Worth page (totals, allocation chart, assets/liabilities lists with valuation history, snapshot history chart, stale badge with recompute); verify RTL tests
- [x] 9.4 Build Loans & EMIs pages (by type, loan form with computed EMI preview, schedule table, confirm-payment dialog showing split, prepayment, rate change, simulation drawer); verify RTL tests for split display and simulation not saving
- [x] 9.5 Extend Overview with new tiles, charts and budget alerts and remove coming-soon states for P1 sections; verify RTL tests

## 10. Integration verification

- [x] 10.1 Playwright E2E: create loan → confirm EMI → dashboard expenses include only interest and net worth reflects reduced liability; verify pass
- [x] 10.2 Playwright E2E: set budget → add expenses past 80% → alert appears once; create goal → contribute → progress updates; verify pass

## Workflow follow-up

- Archive this change after review, before starting `fintrack-p2-wealth-management`.
