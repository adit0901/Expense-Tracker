# Spec Delta

## Purpose

Defines the security guarantees that protect each user's financial data across all FinTrack modules: isolation, abuse protection, safe input and file handling, private logging and an audit trail of financial changes.

## ADDED Requirements

### Requirement: User-level data isolation
Every user-owned resource SHALL be readable and writable only by its owner. Requests for another user's resource SHALL respond HTTP 404 (not 403) so resource existence is not disclosed.

#### Scenario: Accessing another user's transaction
- **WHEN** user A requests a transaction id that belongs to user B
- **THEN** the system responds 404 and returns no data

#### Scenario: Collection scoping
- **WHEN** user A lists transactions
- **THEN** only transactions owned by user A are returned

### Requirement: Authentication required by default
All `/api/v1` endpoints SHALL require a valid access token except registration, login, token refresh, password-reset request and password-reset confirmation.

#### Scenario: Missing token
- **WHEN** a client calls `GET /api/v1/transactions` without a token
- **THEN** the system responds 401 with `error.code` = `not_authenticated`

### Requirement: Rate limiting
The system SHALL rate-limit authentication endpoints per IP and per account identifier (default 5 failed logins per 15 minutes) and general API endpoints per user, responding HTTP 429 with a `Retry-After` header when exceeded.

#### Scenario: Brute-force login
- **WHEN** a client submits a sixth wrong password for the same email within 15 minutes
- **THEN** the system responds 429 with `Retry-After`

### Requirement: Input validation and injection safety
The system SHALL validate all inputs against declared schemas (types, lengths, ranges, enums) and SHALL access the database only through parameterized queries.

#### Scenario: SQL meta-characters in search
- **WHEN** a user searches transactions for `'; DROP TABLE users; --`
- **THEN** the search is treated as literal text and returns matching results or none

### Requirement: Safe file uploads
Uploaded files SHALL be limited to an allow-list of types (PDF, JPEG, PNG, WebP for receipts; CSV for imports) verified by content signature, SHALL NOT exceed 10 MB, SHALL be stored under server-generated names outside the web root, and SHALL be served only to their owner.

#### Scenario: Disguised executable
- **WHEN** a user uploads a file named `receipt.png` whose content is an executable
- **THEN** the system rejects it with 422 `unsupported_file_type`

#### Scenario: Oversized file
- **WHEN** a user uploads an 11 MB receipt
- **THEN** the system rejects it with 413

### Requirement: Sensitive data excluded from logs
Logs SHALL NOT contain passwords, tokens, password-reset links, full account numbers, transaction amounts, descriptions or notes. Account numbers SHALL be masked to their last 4 digits wherever displayed.

#### Scenario: Login log line
- **WHEN** a user logs in
- **THEN** the log line records the outcome and user id but not the password or token

### Requirement: Audit log of financial changes
The system SHALL record an append-only audit entry for every create, update and delete of financial records (accounts, transactions, categories, and later budgets, loans, assets, investments), capturing actor, action, entity type, entity id, timestamp and changed field names.

#### Scenario: Transaction edited
- **WHEN** a user changes the amount of a transaction
- **THEN** an audit entry is written with action `update`, the transaction id and changed field `amount`

#### Scenario: Audit entries immutable
- **WHEN** any API client attempts to modify or delete an audit entry
- **THEN** no endpoint permits it

### Requirement: Atomic financial writes
Operations that change more than one financial record (for example a transfer affecting two accounts, or a CSV import) SHALL be atomic: either all changes are committed or none are.

#### Scenario: Failure mid-import
- **WHEN** a CSV import fails while saving row 40 of 100 in all-or-nothing mode
- **THEN** no rows from that import are persisted

### Requirement: Transport and browser security
The system SHALL serve the application over HTTPS in non-local environments, SHALL send security headers (HSTS, Content-Security-Policy, X-Content-Type-Options, frame denial), and SHALL restrict CORS to configured frontend origins.

#### Scenario: Unknown origin
- **WHEN** a browser at an unconfigured origin calls the API
- **THEN** the CORS preflight is rejected
