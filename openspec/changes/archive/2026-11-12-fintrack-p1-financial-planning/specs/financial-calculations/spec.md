# Spec Delta

## ADDED Requirements

### Requirement: Budget utilization formula
Budget Utilization SHALL equal (Actual Expenses ÷ Budget) × 100, rounded to 2 decimals, where Actual Expenses follows the monthly expense rule (refunds netted, transfers and loan principal excluded). A budget of zero SHALL NOT be allowed.

#### Scenario: Utilization
- **WHEN** actual is 45000.00 and budget is 60000.00
- **THEN** utilization is 75.00

### Requirement: Emergency fund coverage
Emergency Fund Coverage (months) SHALL equal Liquid Savings ÷ Essential Monthly Expenses, where Liquid Savings = bank + cash + wallet balances + assets flagged liquid, and Essential Monthly Expenses = average of the last 3 complete months of expenses in essential categories excluding Loan Interest, plus the current monthly EMI commitment (so interest is not counted twice). When the denominator is zero, coverage SHALL be null.

#### Scenario: Coverage months
- **WHEN** liquid savings are 300000.00 and essential monthly expenses are 50000.00
- **THEN** coverage is 6.00 months

#### Scenario: No essential expenses
- **WHEN** the last 3 months have no essential expenses and no EMIs
- **THEN** coverage is null and displayed "N/A"

### Requirement: Net worth and EMI formulas are centralized
Net worth, EMI, amortization and goal projection formulas defined in the `net-worth`, `loans-emi` and `savings-goals` capabilities SHALL be implemented once in the calculations layer and documented with worked examples in `docs/financial-calculations.md`.

#### Scenario: Worked EMI example documented
- **WHEN** a reviewer opens the calculations document
- **THEN** the EMI example (P = 1000000.00, 12%, 12 months → 88848.79) appears and matches a test case
