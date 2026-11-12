# Proposal: FinTrack P1 – Financial Planning

## Why

After P0 users can see where money goes, but not whether they are on plan or how wealthy they are. P1 adds planning and balance-sheet features — budgets, savings targets, goals, assets, liabilities, loans/EMIs and net worth — so users can steer spending, plan repayments and see their overall financial position. Depends on `fintrack-p0-core-mvp` being implemented and archived.

## What Changes

- Monthly overall and category budgets with utilization, remaining amount, threshold alerts and month-over-month comparison.
- Monthly savings target with planned vs actual tracking; financial goals with contributions, progress, required monthly contribution and estimated completion date.
- Manually valued assets (fixed deposits, gold, real estate, PPF, EPF, NPS, mutual funds, other) with valuation history, and liabilities (other debts) — bank/cash/wallet balances and credit card outstanding come from P0 accounts, never re-entered.
- Loans (home, car, personal, education, other) with reducing-balance EMI, amortization schedule, principal/interest split, payment history, prepayments and repayment simulations.
- New transaction type `loan_payment`: principal reduces the loan liability; only the interest portion counts as an expense (category "Loan Interest").
- Net worth = assets − liabilities, monthly snapshots, month-over-month and year-over-year growth.
- Dashboard extended with net worth, assets, liabilities, outstanding loans, monthly EMI commitments, savings target achievement and the corresponding charts; emergency-fund coverage metric.
- Background worker and Redis introduced (scheduled snapshots, shared rate-limit storage).

## Capabilities

### New Capabilities
- `budgets`: monthly overall and per-category spending budgets, utilization and alerts.
- `savings-goals`: monthly savings targets and named financial goals with contributions and projections.
- `assets-liabilities`: user-declared assets and liabilities with valuation history.
- `loans-emi`: loans, EMI computation, amortization, payments, prepayments and simulations.
- `net-worth`: net worth calculation, snapshots and growth.

### Modified Capabilities
These capabilities are introduced by `fintrack-p0-core-mvp`; this change only ADDS requirements to them (no existing requirement changes):
- `transactions`: adds the `loan_payment` type.
- `financial-calculations`: adds budget utilization, EMI, net worth and emergency-fund formulas.
- `dashboard-overview`: adds planning and balance-sheet tiles and charts.

## Impact

- Backend: new domains `budgets`, `goals`, `assets`, `loans`, `networth`; `tasks/` worker; Alembic migrations for P1 tables (see P0 design ER diagram).
- Infrastructure: Redis and a worker container in Docker Compose.
- Frontend: Budgets, Savings & Goals, Net Worth, Loans & EMIs pages replace their coming-soon states.

## Decisions Requiring Approval

1. **EMI rounding**: EMI rounded half-up to 2 decimals; monthly interest = outstanding × annual rate ÷ 12, rounded to 2 decimals; the final installment absorbs residual rounding. (Some lenders round EMI to the whole rupee — users can override the EMI amount to match their lender.)
2. **EMI payments are never assumed**: the system shows the next due EMI; a payment is recorded only when the user confirms it (P3 recurring rules can pre-fill it as pending).
3. **Goal contributions are tracked records**, optionally linked to a transfer transaction; goals do not earmark account balances automatically.
4. **Mutual funds are manually valued assets in P1**; P2 covers stocks and ETFs with market prices.
5. **Net worth snapshots** are taken automatically on the last day of each month (Asia/Kolkata) and on demand; past snapshots are immutable except via explicit "recompute".

## Out of Scope (P1)

Stock portfolios and market prices (P2), recurring auto-generation of EMIs (P3), push/email notifications (P3; P1 alerts are in-app), floating-rate history modeling beyond manual rate changes, tax computations.
