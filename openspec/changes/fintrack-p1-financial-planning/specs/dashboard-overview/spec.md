# Spec Delta

## ADDED Requirements

### Requirement: Planning and balance-sheet tiles
The Overview page SHALL additionally show: Net Worth, Total Assets, Total Liabilities, Outstanding Loan Amount, Monthly EMI Commitments, and Savings Target vs Achievement for the current month.

#### Scenario: Tiles with data
- **WHEN** a user with loans and a savings target opens Overview
- **THEN** the six tiles show current values computed per their capabilities

#### Scenario: Not configured
- **WHEN** a user has no savings target
- **THEN** the savings target tile offers "Set a target" instead of a value

### Requirement: Planning charts
The Overview page SHALL additionally show net worth growth (from snapshots), asset allocation, and loan outstanding trend over the last 12 months, each linking to its detail page.

#### Scenario: Net worth chart
- **WHEN** a user has 8 monthly snapshots
- **THEN** the net worth chart shows 8 points and links to the Net Worth page

### Requirement: Budget status on dashboard
The Overview page SHALL show overall budget utilization for the current month and the categories that are over budget or past their first alert threshold.

#### Scenario: Over-budget category
- **WHEN** Food is at 112% of budget
- **THEN** Food appears in the dashboard's budget alerts list
