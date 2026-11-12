# dashboard-overview Specification

## Purpose

Gives users an at-a-glance view of their financial health (income, expenses, savings and trends) with period filters and drill-down into detail pages, and grows as later releases add net worth, budgets, loans and investments.

## Requirements

### Requirement: Overview KPI tiles
The Overview page SHALL show, for the selected period: Total Income, Total Expenses, Savings, Savings Rate, and Liquid Funds (current cash + bank balances), each with the change versus the previous equivalent period.

#### Scenario: Monthly KPIs
- **WHEN** a user opens Overview for November 2026
- **THEN** the tiles show November figures and the change versus October 2026

#### Scenario: Not-applicable comparison
- **WHEN** the previous period's value is zero
- **THEN** the percentage change is shown as "—" rather than infinity

### Requirement: Period filter
The dashboard SHALL offer This Month (default), Last Month, This Quarter, This Year, This Financial Year and Custom Range filters; all tiles and charts SHALL respect the selection.

#### Scenario: Custom range
- **WHEN** a user selects 2026-07-15 to 2026-09-15
- **THEN** all tiles and charts recompute for that inclusive range

### Requirement: Income vs expenses chart
The dashboard SHALL show monthly income and expenses as grouped bars for the last 12 months (or the months within the selected range when longer than one month).

#### Scenario: Twelve-month view
- **WHEN** a user with 18 months of data opens Overview
- **THEN** the chart shows the 12 most recent months, including months with zero activity

### Requirement: Savings trend chart
The dashboard SHALL show monthly savings and savings rate over the same months as the income vs expenses chart; months with zero income SHALL show a gap in the rate line.

#### Scenario: Gap for zero income
- **WHEN** a month has zero income
- **THEN** the savings-rate line has no point for that month

### Requirement: Expense category breakdown
The dashboard SHALL show expenses by top-level category for the selected period as a donut chart listing the top 6 categories and grouping the rest as "Other categories".

#### Scenario: Drill-down
- **WHEN** a user clicks the Food segment
- **THEN** the Transactions page opens filtered to Food expenses for that period

### Requirement: Recent transactions
The dashboard SHALL list the 10 most recent transactions with a link to the full Transactions page.

#### Scenario: Recent list
- **WHEN** a user opens Overview
- **THEN** the 10 latest transactions by date are shown

### Requirement: Basic analytics page
The Reports & Analytics section SHALL provide in P0: monthly income report, monthly expense report by category and payment method, and the savings-rate trend, each exportable as CSV.

#### Scenario: Expense by payment method
- **WHEN** a user views October 2026 expenses by payment method
- **THEN** totals per UPI, cash, debit card, credit card and bank transfer are shown and sum to total expenses

### Requirement: Empty and loading states
Each tile and chart SHALL show a skeleton while loading, a meaningful empty state with a call to action when there is no data, and an inline error with retry when loading fails.

#### Scenario: New user
- **WHEN** a user with no transactions opens Overview
- **THEN** the page invites them to add an account and their first transaction

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
