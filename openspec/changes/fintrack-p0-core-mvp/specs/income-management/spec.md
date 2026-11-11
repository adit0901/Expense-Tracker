# Spec Delta

## Purpose

Tracks where a user's income comes from (salary, bonus, freelance, business, rental, dividends and others), including salary gross-to-net breakdowns, and reports income by month and year.

## ADDED Requirements

### Requirement: Income sources
A user SHALL be able to create, edit and deactivate income sources with: name, type (`salary`, `bonus`, `freelance`, `business`, `rental`, `dividend`, `interest`, `other`), default category and default receiving account. Income transactions MAY reference a source.

#### Scenario: Multiple sources
- **WHEN** a user has sources "Acme Corp Salary" and "Freelance Design"
- **THEN** income can be recorded and reported separately per source

### Requirement: Salary breakdown
A salary income transaction MAY include a breakdown of gross salary and named deductions (for example Income Tax/TDS, EPF employee contribution, Professional Tax). Net salary SHALL equal gross minus total deductions and SHALL equal the transaction amount credited to the account.

#### Scenario: Valid breakdown
- **WHEN** a user records salary with gross 150000.00 and deductions TDS 25000.00, EPF 1800.00, Professional Tax 200.00
- **THEN** the net amount credited is 123000.00

#### Scenario: Inconsistent breakdown
- **WHEN** gross minus deductions does not equal the entered net amount
- **THEN** the system responds 422 `salary_breakdown_mismatch`

### Requirement: Income counted at net
Income totals, savings and savings rate SHALL use the net amount received. Gross and deductions SHALL be reported separately and SHALL NOT be counted as expenses.

#### Scenario: TDS not an expense
- **WHEN** a salary with 25000.00 TDS is recorded
- **THEN** monthly expenses do not include the 25000.00 TDS

### Requirement: Income reports
The system SHALL report income per month and per year, broken down by source and category, including gross, deductions and net for salary sources.

#### Scenario: Annual income report
- **WHEN** a user views the 2026 income report
- **THEN** it shows monthly net income totals, per-source totals and the annual total
