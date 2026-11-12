# financial-calculations Specification

## Purpose

The single authoritative source of FinTrack's financial formulas and accounting rules, so every screen, report, export and AI answer shows the same numbers computed the same way.

## Requirements

### Requirement: Single source of calculated figures
All financial figures shown in the UI, reports, exports and (later) AI answers SHALL be computed by the backend. The frontend SHALL only format values it receives and SHALL NOT recompute totals.

#### Scenario: Consistent figures
- **WHEN** the dashboard and the monthly report both show October 2026 expenses
- **THEN** both show the identical value

### Requirement: Decimal arithmetic and rounding
Monetary calculations SHALL use exact decimal arithmetic. Stored amounts SHALL keep 2 decimal places (INR, USD); intermediate results SHALL keep full precision and SHALL round half-up to 2 decimals only when producing a final figure. Percentages SHALL be reported to 2 decimals.

#### Scenario: No float drift
- **WHEN** expenses of 0.10, 0.20 and 0.30 are summed
- **THEN** the total is exactly 0.60

### Requirement: Monthly income and expenses
Monthly Income SHALL be the sum of `income` transactions dated in the period. Monthly Expenses SHALL be the sum of `expense` transactions minus `refund` transactions dated in the period. Transfers, credit card bill payments, salary deductions, and (from later releases) loan principal and investment purchases SHALL be excluded.

#### Scenario: Card purchase and bill in same month
- **WHEN** a user spends 15000.00 on a credit card and pays the 15000.00 bill in the same month
- **THEN** monthly expenses include 15000.00 once

### Requirement: Monthly savings
Monthly Savings SHALL equal Monthly Income minus Monthly Expenses and MAY be negative.

#### Scenario: Overspending
- **WHEN** income is 80000.00 and expenses are 95000.00
- **THEN** savings is -15000.00

### Requirement: Savings rate
Savings Rate SHALL equal (Savings ÷ Income) × 100. When income is zero the savings rate SHALL be reported as not applicable (null), never as zero, infinity or an error.

#### Scenario: Normal savings rate
- **WHEN** income is 120000.00 and expenses are 90000.00
- **THEN** the savings rate is 25.00

#### Scenario: Zero income
- **WHEN** income is 0 and expenses are 5000.00
- **THEN** savings is -5000.00 and the savings rate is null (displayed "N/A")

### Requirement: Category totals
Category totals SHALL include their subcategories' transactions. Each category's share SHALL equal its total ÷ total expenses × 100; when total expenses are zero, shares SHALL be null.

#### Scenario: Category share
- **WHEN** Food is 15000.00 of 60000.00 total expenses
- **THEN** Food's share is 25.00

### Requirement: Period boundaries
Periods SHALL be calendar based in the user's time zone (default Asia/Kolkata): month, quarter (Jan–Mar, Apr–Jun, Jul–Sep, Oct–Dec), calendar year, Indian financial year (1 April–31 March), and custom inclusive date ranges. Transactions SHALL belong to a period by their transaction date, not entry time.

#### Scenario: Financial year
- **WHEN** a user selects FY 2026-27
- **THEN** the period is 2026-04-01 through 2027-03-31 inclusive

#### Scenario: Back-dated entry
- **WHEN** a transaction dated 2026-10-31 is entered on 2026-11-02
- **THEN** it counts toward October 2026

### Requirement: Documented and tested formulas
Every formula in this capability SHALL be documented in `docs/financial-calculations.md` with worked examples, and SHALL be covered by automated tests including zero, negative and boundary cases.

#### Scenario: Formula documentation
- **WHEN** a reviewer opens the calculations document
- **THEN** each formula listed in this spec has a definition and at least one worked example matching a test case
