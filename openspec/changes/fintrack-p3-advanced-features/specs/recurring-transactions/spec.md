# Spec Delta

## Purpose

Automates repetitive money movements (salary, rent, subscriptions, SIPs, insurance premiums, EMIs) by generating scheduled occurrences that users confirm, without ever assuming a real-world payment happened.

## ADDED Requirements

### Requirement: Recurring rules
A user SHALL be able to create, edit, pause, resume and end recurring rules with: a transaction template (type, account, amount, category, payment method, payee, description), frequency (`daily`, `weekly`, `monthly`, `yearly`) with interval, start date, optional end date or occurrence count, and an optional link to a loan (EMI) or goal.

#### Scenario: Monthly rent
- **WHEN** a user creates a monthly rent rule of 25000.00 on the 5th starting 2026-12-05
- **THEN** the next occurrence is shown as 2026-12-05

#### Scenario: Month-end clamping
- **WHEN** a monthly rule starts on 2027-01-31
- **THEN** occurrences fall on 2027-02-28, 2027-03-31 and 2027-04-30

### Requirement: Pending occurrences require confirmation
On each due date the system SHALL generate a pending occurrence. Pending occurrences SHALL NOT affect balances, totals, budgets or net worth until the user confirms them (optionally editing amount or date) or SHALL be skipped if the user skips them.

#### Scenario: Pending rent
- **WHEN** a rent occurrence is generated on 2026-12-05
- **THEN** it appears in "To confirm" and December expenses do not include it until confirmed

#### Scenario: Confirm with change
- **WHEN** a user confirms the electricity occurrence with amount 2340.00 instead of the 2000.00 template
- **THEN** a posted 2340.00 expense is created and the rule template is unchanged

### Requirement: Auto-confirm for income
The system SHALL allow auto-confirm only on income rules; when enabled, occurrences SHALL be posted on the due date and flagged "auto-confirmed" so the user can review or undo them.

#### Scenario: Auto-confirmed salary
- **WHEN** a salary rule with auto-confirm reaches its due date
- **THEN** a posted income transaction exists flagged "auto-confirmed"

### Requirement: EMI rules use the loan payment flow
Rules linked to a loan SHALL generate pending EMI occurrences using the loan's current schedule amount; confirming SHALL use the loans payment flow (principal/interest split).

#### Scenario: EMI confirmation
- **WHEN** a user confirms a pending EMI occurrence
- **THEN** a loan payment is recorded exactly as if confirmed from the loan page

### Requirement: No duplicate occurrences
The system SHALL generate at most one occurrence per rule per due date, including when the generator runs repeatedly or is delayed, and SHALL backfill missed due dates as pending.

#### Scenario: Worker restarts
- **WHEN** the generation job runs twice for the same day
- **THEN** only one occurrence exists for each due rule

#### Scenario: Worker down for 3 days
- **WHEN** the job resumes after missing a daily rule's 3 due dates
- **THEN** 3 pending occurrences are created

### Requirement: Pause and resume
A paused rule SHALL generate no occurrences; on resume, due dates during the pause SHALL NOT be backfilled.

#### Scenario: Paused subscription
- **WHEN** a monthly subscription is paused for October and resumed in November
- **THEN** no October occurrence is created
