# assets-liabilities Specification

## Purpose
Captures what a user owns and owes beyond their transactional accounts (fixed deposits, gold, real estate, retirement schemes, mutual funds, other debts) with dated valuations, as inputs to net worth.

## Requirements

### Requirement: Manual assets
A user SHALL be able to create, edit and close assets of type `fixed_deposit`, `gold`, `real_estate`, `ppf`, `epf`, `nps`, `mutual_fund`, `vehicle`, `other` with name, current value, valuation date, an optional liquidity flag and type-specific details (for example FD principal, rate and maturity date; gold grams).

#### Scenario: Add fixed deposit
- **WHEN** a user adds an FD of principal 200000.00 at 7.10% maturing 2027-11-01 valued 205000.00 today
- **THEN** it appears under assets with value 205000.00

### Requirement: Valuation history
Each value update SHALL create a dated valuation record; the asset's current value SHALL be its latest valuation on or before the reporting date.

#### Scenario: Historical value
- **WHEN** gold was valued 150000.00 on 2026-06-30 and 165000.00 on 2026-10-31
- **THEN** net worth for 2026-09-30 uses 150000.00

### Requirement: No double counting with accounts
Bank, cash and wallet balances and credit card outstanding SHALL come only from financial accounts; the asset and liability types SHALL NOT include bank balances, cash or credit cards. Loan liabilities SHALL come only from loans.

#### Scenario: No bank asset type
- **WHEN** a user tries to create an asset of type `bank`
- **THEN** the system responds 422 and suggests adding a financial account

### Requirement: Other liabilities
A user SHALL be able to record other liabilities (for example money borrowed from family) with name, outstanding amount, as-of date and optional notes, and update the outstanding amount over time with history.

#### Scenario: Update outstanding
- **WHEN** a user lowers a family loan from 100000.00 to 80000.00 on 2026-11-01
- **THEN** both values are kept and 80000.00 is current from that date

### Requirement: Closing assets and liabilities
Closing an asset or liability SHALL keep its history for past net worth and remove it from current totals from the closing date.

#### Scenario: Sold property
- **WHEN** a real-estate asset is closed on 2026-12-15
- **THEN** it counts in net worth before 2026-12-15 and not after
