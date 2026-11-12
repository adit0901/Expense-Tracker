# user-profile Specification

## Purpose

Lets each user manage their profile and preferences (currency, theme, locale, date format, number grouping) that shape how FinTrack presents their data.

## Requirements

### Requirement: View and update profile
An authenticated user SHALL be able to view and update their full name. Changing the email SHALL require the current password.

#### Scenario: Update name
- **WHEN** a user changes their full name
- **THEN** the new name is returned on subsequent profile reads

#### Scenario: Email change without password
- **WHEN** a user changes their email without supplying the current password
- **THEN** the system responds 422 and the email is unchanged

### Requirement: Preferences with defaults
Each user SHALL have preferences with these defaults: preferred currency `INR`, theme `system`, locale `en-IN`, date format `DD/MM/YYYY`, number grouping Indian (lakh/crore), week start Monday.

#### Scenario: New user defaults
- **WHEN** a new user reads their preferences
- **THEN** the defaults listed above are returned

### Requirement: Reporting currency is INR
The system SHALL compute and report all aggregate figures in INR. The preferred-currency preference SHALL accept only `INR` until multi-currency reporting is introduced.

#### Scenario: Unsupported currency preference
- **WHEN** a user sets preferred currency to `EUR`
- **THEN** the system responds 422 `unsupported_currency`

### Requirement: Indian number formatting
When number grouping is Indian, the frontend SHALL format amounts with lakh/crore grouping (for example `₹12,34,567.89`); when international, with thousands grouping (`₹1,234,567.89`).

#### Scenario: Indian grouping
- **WHEN** a user with Indian grouping views an amount of 1234567.89 INR
- **THEN** it is displayed as `₹12,34,567.89`

### Requirement: Account deletion
A user SHALL be able to permanently delete their account after re-entering their password; all their financial data and uploaded files SHALL be deleted, while audit entries SHALL be retained in anonymized form.

#### Scenario: Delete account
- **WHEN** a user confirms account deletion with the correct password
- **THEN** they can no longer log in and none of their records are retrievable
