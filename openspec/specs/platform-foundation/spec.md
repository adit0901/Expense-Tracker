# platform-foundation Specification

## Purpose

Defines the cross-cutting API and runtime conventions every FinTrack module relies on: versioning, response and error shapes, pagination, health checks, logging and configuration.

## Requirements

### Requirement: Versioned REST API
The system SHALL expose all business endpoints under a version prefix `/api/v1`, grouped by business domain (for example `/api/v1/auth`, `/api/v1/transactions`).

#### Scenario: Versioned path
- **WHEN** a client calls `GET /api/v1/accounts` with a valid token
- **THEN** the system responds from the accounts domain

#### Scenario: Unversioned path rejected
- **WHEN** a client calls `GET /accounts`
- **THEN** the system responds with HTTP 404

### Requirement: Consistent success response envelope
The system SHALL return successful JSON responses as `{"data": ..., "meta": {...}}`, where `meta` carries pagination and request metadata when applicable.

#### Scenario: Single resource
- **WHEN** a client fetches one transaction
- **THEN** the response body contains the transaction under `data`

### Requirement: Consistent error response
The system SHALL return errors as `{"error": {"code": <stable machine code>, "message": <human-readable>, "details": [...], "request_id": <id>}}` with an appropriate HTTP status. Validation errors SHALL use HTTP 422 and list each invalid field in `details`.

#### Scenario: Validation error
- **WHEN** a client creates a transaction with a missing amount
- **THEN** the system responds 422 with `error.code` = `validation_error` and a `details` entry for `amount`

#### Scenario: Unexpected error hides internals
- **WHEN** an unhandled server error occurs
- **THEN** the system responds 500 with `error.code` = `internal_error` and no stack trace or SQL in the body

### Requirement: Pagination, sorting and filtering for collections
Collection endpoints SHALL support `page` and `page_size` (default 25, maximum 100) and return `meta.page`, `meta.page_size`, `meta.total_items` and `meta.total_pages`. Sorting SHALL be restricted to an allow-listed set of fields per endpoint.

#### Scenario: Page size capped
- **WHEN** a client requests `page_size=500`
- **THEN** the system responds 422 indicating the maximum page size is 100

#### Scenario: Disallowed sort field
- **WHEN** a client requests sorting by a field not in the allow-list
- **THEN** the system responds 422 with `error.code` = `invalid_sort`

### Requirement: Monetary values serialized as strings
The API SHALL serialize monetary amounts, rates and quantities as decimal strings (for example `"1250.50"`) together with an ISO 4217 currency code, never as binary floating-point numbers.

#### Scenario: Amount serialization
- **WHEN** a client fetches an expense of 1250.5 INR
- **THEN** the response contains `"amount": "1250.50"` and `"currency": "INR"`

### Requirement: Health checks
The system SHALL expose unauthenticated `GET /health/live` (process up) and `GET /health/ready` (database reachable and migrations current). Health responses SHALL NOT include secrets or user data.

#### Scenario: Database down
- **WHEN** the database is unreachable and `/health/ready` is called
- **THEN** the system responds 503 with the failing dependency named

#### Scenario: Liveness
- **WHEN** the API process is running and `/health/live` is called
- **THEN** the system responds 200

### Requirement: Structured request logging
The system SHALL emit one structured JSON log line per request containing request id, method, route template, status, duration and user id (if authenticated), and SHALL return the request id in an `X-Request-ID` response header.

#### Scenario: Request id propagated
- **WHEN** any API request completes
- **THEN** the response includes `X-Request-ID` and a log line with the same id exists

### Requirement: Environment-based configuration
The system SHALL read secrets and environment settings only from environment variables or a secret store, and SHALL refuse to start in production mode when required secrets (database URL, JWT signing key) are missing or set to development defaults.

#### Scenario: Missing secret in production
- **WHEN** the backend starts with `APP_ENV=production` and the default JWT key
- **THEN** startup fails with a clear configuration error

### Requirement: API documentation
The system SHALL publish an OpenAPI specification describing every v1 endpoint, request and response schema, available in non-production environments at `/api/docs`.

#### Scenario: Docs available in development
- **WHEN** a developer opens `/api/docs` with `APP_ENV=development`
- **THEN** interactive API documentation is shown
