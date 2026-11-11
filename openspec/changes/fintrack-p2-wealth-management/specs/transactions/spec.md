# Spec Delta

## ADDED Requirements

### Requirement: Investment ledger transaction types
The system SHALL support `investment_buy`, `investment_sell` and `dividend` ledger transaction types, created only through the investments capability when a buy, sell or dividend is linked to a bank account. `investment_buy` debits the account and `investment_sell` credits it; neither SHALL count as income or expense.

#### Scenario: Funded buy
- **WHEN** a user records a 35020.00 TCS buy funded from "HDFC Savings"
- **THEN** the bank balance decreases by 35020.00 and monthly expenses are unchanged

#### Scenario: Sale proceeds
- **WHEN** a sale with net proceeds 15185.00 is credited to the bank account
- **THEN** the bank balance increases by 15185.00 and monthly income is unchanged

### Requirement: Dividends count as income
A `dividend` ledger transaction SHALL credit the linked account with the net dividend in INR and SHALL count as income in the "Dividends" category. Dividends not linked to an account SHALL still count as income in reports, using their recorded INR value.

#### Scenario: Dividend income
- **WHEN** a 652.50 INR-equivalent net dividend is recorded
- **THEN** monthly income includes 652.50 under Dividends exactly once
