# Spec Delta

## Purpose

Tracks a user's loans (home, car, personal, education, other) and their EMIs: schedules, principal/interest split, payments, prepayments and what-if simulations, so users understand their repayment commitments and the true cost of borrowing.

## ADDED Requirements

### Requirement: Manage loans
A user SHALL be able to create, edit and close loans with: type (`home`, `car`, `personal`, `education`, `other`), lender, original principal, annual interest rate (≥ 0), tenure in months, start date, first EMI date, EMI amount (computed by default, overridable to match the lender), and the outstanding principal as of a date for loans already in progress.

#### Scenario: New home loan
- **WHEN** a user adds a 5000000.00 home loan at 8.5% for 240 months
- **THEN** the computed EMI is 43391.16

#### Scenario: Existing loan mid-tenure
- **WHEN** a user adds a car loan that started 2 years ago with outstanding principal 380000.00 as of 2026-11-01
- **THEN** the schedule starts from 2026-11-01 with that outstanding principal and the remaining tenure

### Requirement: Reducing-balance EMI
EMI SHALL be P × r × (1+r)^n ÷ ((1+r)^n − 1), where P is principal, r = annual rate ÷ 12 ÷ 100 and n is tenure in months, rounded half-up to 2 decimals. When the rate is zero, EMI SHALL be P ÷ n rounded to 2 decimals.

#### Scenario: Standard EMI
- **WHEN** P = 1000000.00, rate = 12%, n = 12
- **THEN** EMI is 88848.79

#### Scenario: Zero-interest loan
- **WHEN** P = 100000.00, rate = 0%, n = 12
- **THEN** EMI is 8333.33 and every installment's interest is 0.00

### Requirement: Amortization schedule
The system SHALL generate a schedule with, per installment: number, due date, payment, interest = outstanding × r (rounded to 2 decimals), principal = payment − interest, and closing outstanding. The final installment SHALL repay exactly the remaining principal plus its interest, so the closing outstanding is 0.00.

#### Scenario: Final installment adjustment
- **WHEN** the schedule for P = 1000000.00 at 12% for 12 months is generated
- **THEN** installment 1 has interest 10000.00 and principal 78848.79, the final installment is 88848.76, and total interest is 66185.45

#### Scenario: Zero-interest final adjustment
- **WHEN** the schedule for P = 100000.00 at 0% for 12 months is generated
- **THEN** installments 1–11 are 8333.33 and installment 12 is 8333.37

### Requirement: EMI payments recorded only on confirmation
The system SHALL show the next EMI due date and amount but SHALL NOT record a payment until the user confirms it. A confirmed payment SHALL create a `loan_payment` transaction from a chosen account with principal and interest components and SHALL update the outstanding principal.

#### Scenario: Confirm EMI
- **WHEN** a user confirms installment 1 of the 12% example from their bank account
- **THEN** the bank balance decreases by 88848.79, outstanding becomes 921151.21, and monthly expenses increase by 10000.00 only

#### Scenario: Due but unconfirmed
- **WHEN** an EMI due date passes without confirmation
- **THEN** the EMI is shown as "Due — not recorded" and outstanding is unchanged

### Requirement: Prepayments
A user SHALL be able to record a prepayment (date, amount, source account) and choose to reduce tenure (keep EMI) or reduce EMI (keep tenure); the schedule SHALL be regenerated from that date. Prepayment SHALL reduce outstanding principal and SHALL NOT count as an expense.

#### Scenario: Reduce tenure
- **WHEN** a user prepays 500000.00 on a home loan choosing "reduce tenure"
- **THEN** the EMI is unchanged, the remaining number of installments decreases and total interest payable decreases

### Requirement: Repayment simulation
A user SHALL be able to simulate, without saving, a one-time prepayment, a recurring extra monthly payment, or a rate change, and see new tenure or EMI, total interest payable, interest saved and new end date versus the current plan.

#### Scenario: Extra monthly payment
- **WHEN** a user simulates paying 5000.00 extra each month
- **THEN** the result shows the reduced tenure, new end date and interest saved, and the loan is not changed

### Requirement: Loan summaries
The system SHALL show per loan: outstanding principal, principal and interest paid to date, total interest payable over the remaining schedule, remaining installments, end date and payment history; and across loans: total outstanding and total monthly EMI commitment of active loans.

#### Scenario: Total EMI commitment
- **WHEN** a user has active EMIs of 43391.16 and 12500.00
- **THEN** the monthly EMI commitment is 55891.16

### Requirement: Interest rate changes
A user SHALL be able to record a rate change effective from a date for floating-rate loans, choosing to keep EMI (tenure adjusts) or keep tenure (EMI adjusts); the schedule SHALL be regenerated from that date.

#### Scenario: Rate hike keeping EMI
- **WHEN** a rate rises from 8.5% to 9.0% with "keep EMI"
- **THEN** the remaining tenure increases and the EMI amount is unchanged

#### Scenario: EMI below interest
- **WHEN** a rate change with "keep EMI" makes the EMI smaller than the monthly interest
- **THEN** the system rejects the option and asks the user to increase the EMI or choose "keep tenure"
