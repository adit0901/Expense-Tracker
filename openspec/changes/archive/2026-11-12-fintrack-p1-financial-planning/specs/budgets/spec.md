# Spec Delta

## Purpose

Lets users plan monthly spending with an overall budget and per-category budgets, and see how actual spending compares, with alerts before they overspend.

## ADDED Requirements

### Requirement: Monthly budgets
A user SHALL be able to set, for a calendar month, an overall expense budget and budgets for individual expense categories (top-level or subcategory). Budget amounts SHALL be positive with 2 decimals.

#### Scenario: Set category budget
- **WHEN** a user sets a Food budget of 12000.00 for November 2026
- **THEN** the Budgets page shows Food with budget 12000.00 for November 2026

### Requirement: Budget utilization and remaining
For each budget the system SHALL show actual expenses (per `financial-calculations`), utilization = actual ÷ budget × 100, and remaining = budget − actual (negative when overspent).

#### Scenario: Partially used
- **WHEN** Food budget is 12000.00 and Food expenses are 9000.00
- **THEN** utilization is 75.00 and remaining is 3000.00

#### Scenario: Overspent
- **WHEN** Food expenses reach 13500.00 on a 12000.00 budget
- **THEN** utilization is 112.50, remaining is -1500.00 and the budget is marked over budget

### Requirement: Category budget roll-up
A top-level category budget's actual SHALL include its subcategories. When the sum of category budgets exceeds the overall budget, the system SHALL warn but allow saving.

#### Scenario: Category budgets exceed overall
- **WHEN** category budgets sum to 70000.00 against a 60000.00 overall budget
- **THEN** a warning is shown and the budgets are saved

### Requirement: Copy budgets forward
A user SHALL be able to copy all budgets from a previous month into a month that has none.

#### Scenario: Copy previous month
- **WHEN** a user copies October 2026 budgets into an empty December 2026
- **THEN** December has the same overall and category budget amounts

### Requirement: Spending alerts
Each budget SHALL have configurable alert thresholds (default 80% and 100%). When utilization first crosses a threshold within a month, the system SHALL create one in-app alert for that budget and threshold.

#### Scenario: Threshold crossed once
- **WHEN** a new expense raises Food utilization from 78% to 83%
- **THEN** one 80% alert is created, and further expenses below 100% create no additional alert

#### Scenario: Expense deleted
- **WHEN** utilization drops below a threshold after a deletion and later crosses it again in the same month
- **THEN** no duplicate alert is created for that month and threshold

### Requirement: Monthly budget comparison
The system SHALL compare budget vs actual for a category or overall across the last 6 or 12 months.

#### Scenario: Six-month comparison
- **WHEN** a user views Food over the last 6 months
- **THEN** each month's budget, actual and utilization are shown, with "No budget" for months without one
