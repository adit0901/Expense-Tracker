# financial-accounts Specification

## Purpose

Represents the places a user's money lives or is owed (bank accounts, cash, credit cards, wallets) so every transaction is anchored to an account and balances can be derived reliably.

## Requirements

### Requirement: Manage financial accounts
A user SHALL be able to create, view, edit, archive and unarchive accounts with: name, type (`bank`, `cash`, `credit_card`, `wallet`), institution (optional), last 4 digits (optional), currency (`INR` in P0), opening balance and opening date.

#### Scenario: Create bank account
- **WHEN** a user creates a bank account "HDFC Savings" with opening balance 50000.00 on 2026-01-01
- **THEN** the account is listed with current balance 50000.00 before any transactions

#### Scenario: Full account number rejected
- **WHEN** a user enters more than 4 digits in the last-4 field
- **THEN** the system responds 422

### Requirement: Derived account balance
An account's current balance SHALL equal its opening balance plus the signed sum of its posted transactions on or after the opening date. Balances SHALL NOT be stored as an independently editable field.

#### Scenario: Balance after transactions
- **WHEN** a bank account opened with 50000.00 receives income 80000.00 and records expenses of 12000.00
- **THEN** its balance is 118000.00

### Requirement: Credit card balances represent amounts owed
For `credit_card` accounts the balance SHALL represent the outstanding amount owed: purchases increase it and bill payments (transfers into the card) decrease it. The UI SHALL present it as "Outstanding".

#### Scenario: Card purchase and payment
- **WHEN** a card with outstanding 0 records purchases of 15000.00 and later a 10000.00 bill payment from a bank account
- **THEN** the card outstanding is 5000.00 and the bank balance decreased by 10000.00

### Requirement: Archive instead of delete when history exists
An account with transactions SHALL NOT be hard-deleted; it SHALL be archived, hidden from entry forms, and still included in historical reports. An account with no transactions MAY be deleted.

#### Scenario: Delete account with history
- **WHEN** a user deletes an account that has transactions
- **THEN** the system responds 409 `account_has_transactions` and offers archiving

#### Scenario: Archived account in reports
- **WHEN** a user views last year's expense report after archiving an account
- **THEN** that account's past transactions are still included

#### Scenario: Unarchive an account
- **WHEN** a user unarchives an archived account
- **THEN** the account is active again: it appears in account lists and entry forms, counts toward the accounts summary, and the change is recorded in the audit log
- **AND** unarchiving an account that is already active succeeds without changing it

### Requirement: Accounts summary
The system SHALL provide a summary of total cash and bank balances (liquid funds) and total credit card outstanding across non-archived accounts.

#### Scenario: Summary totals
- **WHEN** a user has bank 118000.00, cash 2000.00 and card outstanding 5000.00
- **THEN** the summary shows liquid funds 120000.00 and card outstanding 5000.00
