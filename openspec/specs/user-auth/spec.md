# user-auth Specification

## Purpose

Lets people create a FinTrack account, sign in and out securely, keep sessions alive safely, and recover access when they forget their password.

## Requirements

### Requirement: User registration
The system SHALL let a person register with full name, email and password. Emails SHALL be unique case-insensitively. Passwords SHALL be at least 10 characters and SHALL NOT appear in a common-password list. Passwords SHALL be stored only as a slow salted hash.

#### Scenario: Successful registration
- **WHEN** a person registers with a new email and a valid password
- **THEN** the account is created with default preferences and default categories, and the response contains no password or hash

#### Scenario: Duplicate email
- **WHEN** a person registers with `Asha@Example.com` and `asha@example.com` already exists
- **THEN** the system responds 409 `email_taken`

#### Scenario: Weak password
- **WHEN** a person registers with password `password123`
- **THEN** the system responds 422 explaining the password requirement

### Requirement: Login
The system SHALL authenticate a user by email and password and issue a short-lived access token (15 minutes) and a refresh token (7 days) delivered as an httpOnly, Secure, SameSite=Strict cookie. Failed logins SHALL return the same error regardless of whether the email exists.

#### Scenario: Valid credentials
- **WHEN** a user logs in with correct credentials
- **THEN** the system returns an access token and sets the refresh cookie

#### Scenario: Unknown email or wrong password
- **WHEN** a user logs in with an unknown email or a wrong password
- **THEN** the system responds 401 `invalid_credentials` in both cases

### Requirement: Token refresh with rotation
The system SHALL issue a new access token and a new refresh token when presented a valid refresh token, and SHALL invalidate the used refresh token. Reuse of an already-rotated refresh token SHALL revoke every refresh token of that session family.

#### Scenario: Normal refresh
- **WHEN** the client calls refresh with a valid refresh cookie
- **THEN** a new access token and a new refresh cookie are issued and the old refresh token stops working

#### Scenario: Refresh token reuse
- **WHEN** an already-used refresh token is presented
- **THEN** the system responds 401 and revokes all tokens in that session family

### Requirement: Logout
The system SHALL revoke the current refresh token and clear the refresh cookie on logout.

#### Scenario: Logout
- **WHEN** a logged-in user logs out
- **THEN** subsequent refresh attempts with that token fail with 401

### Requirement: Password reset
The system SHALL let a user request a password reset by email and SHALL respond identically whether or not the email exists. Reset tokens SHALL be single-use, expire after 30 minutes and be stored only as hashes. A successful reset SHALL revoke all of the user's refresh tokens.

#### Scenario: Request for unknown email
- **WHEN** a reset is requested for an unregistered email
- **THEN** the system responds 202 with the same message as for a registered email and sends no email

#### Scenario: Successful reset
- **WHEN** a user submits a valid unexpired reset token and a valid new password
- **THEN** the password is changed, the token is consumed, and existing sessions are signed out

#### Scenario: Expired token
- **WHEN** a reset token older than 30 minutes is submitted
- **THEN** the system responds 400 `reset_token_invalid`

### Requirement: Change password
An authenticated user SHALL be able to change their password by supplying the current password; other sessions SHALL be revoked on success.

#### Scenario: Wrong current password
- **WHEN** a user submits an incorrect current password
- **THEN** the system responds 400 and the password is unchanged
