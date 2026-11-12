# net-worth Specification

## Purpose
Shows a user's overall financial position — total assets minus total liabilities — today and over time, with a breakdown by type and month-over-month and year-over-year growth.

## Requirements

### Requirement: Net worth calculation
Net worth SHALL equal total assets − total liabilities as of a date. Assets: bank, cash and wallet account balances (zero or positive), manual asset valuations, and (from P2) investment holdings value in INR. Liabilities: credit card outstanding, loan outstanding principal, other liabilities, and negative balances of bank accounts (overdraft).

#### Scenario: Net worth today
- **WHEN** a user has bank 300000.00, FD 205000.00, gold 165000.00, card outstanding 25000.00 and home loan outstanding 4800000.00
- **THEN** total assets are 670000.00, total liabilities 4825000.00 and net worth -4155000.00

#### Scenario: Overdraft counted as liability
- **WHEN** a bank account balance is -2000.00
- **THEN** 2000.00 is counted in liabilities, not as a negative asset

### Requirement: Breakdown and allocation
The system SHALL show assets and liabilities grouped by type with each group's amount and share of its total.

#### Scenario: Asset allocation
- **WHEN** a user views the Net Worth page
- **THEN** asset groups (bank & cash, fixed deposits, gold, real estate, retirement schemes, mutual funds, other) are listed with shares summing to 100%

### Requirement: Net worth snapshots
The system SHALL store a snapshot (date, totals and per-type breakdown) automatically at each month end (Asia/Kolkata) and when the user requests one. Snapshots SHALL NOT change when underlying data is later edited, unless the user explicitly recomputes a snapshot.

#### Scenario: Month-end snapshot
- **WHEN** the worker runs after 2026-11-30 ends
- **THEN** a snapshot dated 2026-11-30 exists for every active user

#### Scenario: Back-dated edit
- **WHEN** a user edits an October transaction after the October snapshot was taken
- **THEN** the October snapshot is unchanged and the page indicates it may be outdated with a "Recompute" option

### Requirement: Net worth growth
The system SHALL show net worth history from snapshots and the change versus the previous month-end and the same month of the previous year, in amount and percent. Percent change SHALL be null when the base is zero, and SHALL be computed on the absolute base when the base is negative.

#### Scenario: Month over month
- **WHEN** the October snapshot is 1000000.00 and current net worth is 1050000.00
- **THEN** month-over-month change is 50000.00 (5.00%)

#### Scenario: Missing year-ago snapshot
- **WHEN** no snapshot exists for a year earlier
- **THEN** year-over-year change is shown as "—"
