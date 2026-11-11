# Spec Delta

## Purpose

Produces deterministic, explainable insights from a user's data — monthly summaries, unusual spending, and budget and savings suggestions — that work without any AI provider.

## ADDED Requirements

### Requirement: Monthly financial summary
After each month ends the system SHALL produce a summary with income, expenses, savings, savings rate, top 3 expense categories, changes versus the previous month, budget results, net worth change, and goal progress.

#### Scenario: November summary
- **WHEN** November 2026 ends
- **THEN** a November summary is available on the Overview and Reports pages

### Requirement: Unusual spending detection
The system SHALL flag a category's monthly spending as unusual when it exceeds its trailing 6-month average by more than 50% and by at least 2000.00, and a single expense as unusual when it exceeds 3 times the category's median transaction (minimum 3 months of history).

#### Scenario: Category spike
- **WHEN** Shopping averaged 8000.00 over 6 months and is 14000.00 this month
- **THEN** Shopping is flagged with the comparison shown

#### Scenario: Insufficient history
- **WHEN** a category has less than 3 months of history
- **THEN** no unusual-spending flag is produced for it

### Requirement: Budget and savings suggestions
The system SHALL suggest category budgets from the trailing 3-month average for categories without budgets, and suggest a savings target based on the trailing 3-month average savings; each suggestion SHALL show the data it is based on.

#### Scenario: Budget suggestion
- **WHEN** Food has no budget and averaged 11500.00 over 3 months
- **THEN** a suggested Food budget of 11500.00 is shown with that basis

### Requirement: Insights are explainable and dismissible
Each insight SHALL show the rule and figures that produced it, and users SHALL be able to dismiss it.

#### Scenario: Dismiss
- **WHEN** a user dismisses an unusual-spending insight
- **THEN** it no longer appears for that month
