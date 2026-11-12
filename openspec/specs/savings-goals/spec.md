# savings-goals Specification

## Purpose
Helps users save deliberately: a monthly savings target compared with actual savings, and named financial goals (emergency fund, vacation, house, retirement) tracked toward a target amount and deadline.

## Requirements

### Requirement: Monthly savings target
A user SHALL be able to set a monthly savings target amount, effective from a month onward until changed. The system SHALL show target, actual savings (per `financial-calculations`) and achievement = actual ÷ target × 100.

#### Scenario: Target achieved
- **WHEN** the target is 30000.00 and actual savings are 36000.00
- **THEN** achievement is 120.00 and the month is marked achieved

#### Scenario: Negative savings
- **WHEN** actual savings are -5000.00 against a 30000.00 target
- **THEN** achievement is shown as 0 with the shortfall of 35000.00

### Requirement: Financial goals
A user SHALL be able to create, edit, pause, complete and delete goals with: name, type (`emergency_fund`, `vacation`, `house`, `vehicle`, `education`, `retirement`, `other`), target amount, optional target date, and optional starting amount.

#### Scenario: Create goal
- **WHEN** a user creates "Emergency Fund" with target 300000.00 by 2027-06-30
- **THEN** the goal is listed with progress 0% (or the starting amount's share)

### Requirement: Goal contributions
A user SHALL be able to record contributions and withdrawals against a goal (date, amount, optional link to a transfer transaction). The goal's current amount SHALL equal starting amount + contributions − withdrawals and SHALL NOT go below zero.

#### Scenario: Contribution
- **WHEN** a user records a 25000.00 contribution to a goal at 50000.00
- **THEN** the current amount is 75000.00

#### Scenario: Over-withdrawal
- **WHEN** a withdrawal exceeds the current amount
- **THEN** the system responds 422

### Requirement: Goal progress and projections
For each goal the system SHALL show progress % (capped display at 100% with "achieved"), remaining amount, required monthly contribution to meet the target date, and an estimated completion date based on the average net monthly contribution over the last 3 months. Projections SHALL be labeled as estimates.

#### Scenario: Required contribution
- **WHEN** 225000.00 remains and 9 full months are left before the target date
- **THEN** the required monthly contribution is 25000.00

#### Scenario: No recent contributions
- **WHEN** the 3-month average contribution is zero or negative
- **THEN** the estimated completion date is shown as "Cannot estimate"

#### Scenario: Deadline passed
- **WHEN** the target date has passed and the goal is not achieved
- **THEN** the goal is marked overdue and required monthly contribution is not shown
