# Spec Delta

## Purpose

Records every money movement a user makes, classified by type, account, category and payment method, so balances, income, expenses and savings can be calculated correctly and searched, imported and exported.

## ADDED Requirements

### Requirement: Transaction types
Every transaction SHALL have exactly one type. P0 types: `income`, `expense`, `transfer`, `refund`. Later releases add `loan_payment`, `investment_buy`, `investment_sell` and `dividend`. Only `income` and `expense` (net of `refund`) SHALL contribute to income and expense totals.

#### Scenario: Transfer excluded from expenses
- **WHEN** a user transfers 20000.00 from a bank account to a wallet
- **THEN** monthly expenses and income are unchanged and both account balances are updated

### Requirement: Record income and expense
A user SHALL be able to create income and expense transactions with: account, date, amount (> 0, max 2 decimal places), category, payment method (expenses), payee/source (optional), description (optional, ≤ 255 chars), notes (optional), tags (optional).

#### Scenario: Create expense
- **WHEN** a user records a 450.00 Food expense paid by UPI from "HDFC Savings" on 2026-11-10
- **THEN** the transaction is saved and the account balance decreases by 450.00

#### Scenario: Non-positive amount
- **WHEN** a user submits an amount of 0 or -100
- **THEN** the system responds 422; direction is expressed by type, never by sign

#### Scenario: Too many decimals
- **WHEN** a user submits 10.555
- **THEN** the system responds 422

### Requirement: Payment methods
Expense transactions SHALL record a payment method from: `upi`, `cash`, `debit_card`, `credit_card`, `bank_transfer`, `other`. A `credit_card` payment method SHALL require a `credit_card` account.

#### Scenario: Card method with bank account
- **WHEN** a user records an expense with method `credit_card` against a bank account
- **THEN** the system responds 422 `payment_method_account_mismatch`

### Requirement: Transfers between own accounts
A transfer SHALL move an amount from one of the user's accounts to another, decreasing the source and increasing the destination (or decreasing a credit card's outstanding). Source and destination SHALL differ. A credit card bill payment SHALL be recorded as a transfer.

#### Scenario: Credit card bill payment
- **WHEN** a user pays 10000.00 from a bank account to a credit card
- **THEN** it is recorded as a transfer, the card outstanding drops by 10000.00 and monthly expenses are unchanged

#### Scenario: Same account
- **WHEN** a user creates a transfer with identical source and destination
- **THEN** the system responds 422

### Requirement: Refunds
A refund SHALL reference an expense category (and optionally the original expense) and SHALL reduce that category's expense total for the month in which the refund is dated.

#### Scenario: Partial refund
- **WHEN** a 3000.00 Shopping expense is followed by a 1000.00 Shopping refund in the same month
- **THEN** Shopping expenses for that month total 2000.00

### Requirement: Edit and delete transactions
A user SHALL be able to edit any field of their transaction and delete it after confirmation; balances and aggregates SHALL reflect the change immediately.

#### Scenario: Delete expense
- **WHEN** a user confirms deletion of a 450.00 expense
- **THEN** the account balance increases by 450.00 and the expense disappears from reports

### Requirement: Search and filter transactions
The transaction list SHALL support filtering by date range, type, account, category (including subcategories), payment method, amount range, tag and free-text search over payee, description and notes, sorted by date descending by default.

#### Scenario: Filter by category and date
- **WHEN** a user filters Food expenses between 2026-10-01 and 2026-10-31
- **THEN** only Food (and Food subcategory) expenses dated in October 2026 are returned with a matching total

### Requirement: CSV import with preview
A user SHALL be able to upload a CSV, map its columns (date, amount, type or debit/credit columns, description, category, payment method), choose a target account and date format, preview parsed rows with per-row errors and duplicate flags, and confirm import of the valid rows.

#### Scenario: Preview flags errors
- **WHEN** a CSV contains a row with an unparseable date
- **THEN** the preview marks that row invalid with the reason and it is excluded from import

#### Scenario: Confirmed import
- **WHEN** a user confirms an import of 98 valid rows
- **THEN** 98 transactions are created atomically and tagged with the import batch id

#### Scenario: Undo import
- **WHEN** a user undoes an import batch within 24 hours
- **THEN** all transactions from that batch are deleted

### Requirement: CSV export
A user SHALL be able to export the currently filtered transaction list as CSV (UTF-8, header row, ISO dates, plain decimal amounts). Cell values starting with `=`, `+`, `-` or `@` SHALL be escaped to prevent formula injection.

#### Scenario: Formula injection prevented
- **WHEN** an exported description is `=HYPERLINK("x")`
- **THEN** the CSV cell is written as `'=HYPERLINK("x")`

### Requirement: Receipt attachments
A user SHALL be able to attach up to 5 receipt files (per the safe-upload rules) to a transaction, view and download them, and delete them. Deleting a transaction SHALL delete its receipts.

#### Scenario: Attach receipt
- **WHEN** a user attaches a 2 MB JPEG to an expense
- **THEN** the expense shows the attachment and only that user can download it

### Requirement: Duplicate transaction detection
On create and import the system SHALL flag likely duplicates: same account, same type, same amount, and dates within 1 day, with similar payee/description. Flagged transactions SHALL require explicit user confirmation; the system SHALL NOT silently discard them.

#### Scenario: Manual duplicate
- **WHEN** a user enters a 450.00 Food expense on the same account one day after an identical one
- **THEN** the system warns of a possible duplicate and saves only after the user confirms

#### Scenario: Import duplicates
- **WHEN** an imported CSV contains rows matching existing transactions
- **THEN** those rows are flagged in the preview and are unselected by default
