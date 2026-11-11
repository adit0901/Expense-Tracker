# Spec Delta

## ADDED Requirements

### Requirement: Pending transaction status
Transactions SHALL have a status of `posted` or `pending`. Only recurring occurrences SHALL be created as `pending`. Pending transactions SHALL be excluded from balances, income, expenses, budgets, net worth, reports and exports until confirmed.

#### Scenario: Pending excluded
- **WHEN** a pending 25000.00 rent occurrence exists
- **THEN** the account balance and monthly expenses exclude it

#### Scenario: Pending listed separately
- **WHEN** a user views Transactions
- **THEN** pending items appear in a separate "To confirm" list, not in the posted list

### Requirement: Duplicate check on confirmation
Confirming a pending occurrence SHALL run duplicate detection against posted transactions so a payment the user already entered manually is not counted twice.

#### Scenario: Already entered manually
- **WHEN** a user confirms a rent occurrence matching a rent expense they already entered
- **THEN** the system warns of a possible duplicate and offers to skip the occurrence instead
