# Spec Delta

## Purpose

Organizes a user's Indian and US equity investments into investment accounts and holdings, derived from their recorded transactions and valued from market data, in both the security's currency and INR.

## ADDED Requirements

### Requirement: Investment accounts
A user SHALL be able to create, edit and close investment accounts with name, broker, market (`IN` or `US`) and base currency (`INR` for IN, `USD` for US).

#### Scenario: Create US account
- **WHEN** a user creates "US Broker" with market `US`
- **THEN** the account's currency is USD and it accepts only US-listed securities

### Requirement: Securities
The system SHALL identify securities by exchange and symbol: `NSE` and `BSE` (INR) and `NASDAQ`, `NYSE`, `NYSE_ARCA` (USD), with name, type (`stock`, `etf`), optional ISIN and optional sector. Users SHALL be able to search provider-backed securities or add a security manually when no provider is configured.

#### Scenario: Same company on two exchanges
- **WHEN** a user holds RELIANCE on NSE in one account and BSE in another
- **THEN** they are tracked as two securities with separate prices

#### Scenario: Manual security
- **WHEN** no market data provider is configured and a user adds "INFY" on NSE manually
- **THEN** the security is available for transactions in that user's portfolio

### Requirement: Derived holdings
A holding (account + security) SHALL be derived from the account's investment transactions: quantity, average cost per unit (security currency), total cost (security currency and INR), and SHALL NOT be directly editable. Holdings with zero quantity SHALL be shown only in history.

#### Scenario: Holding after buys
- **WHEN** a user buys 10 TCS at 3500.00 and then 10 at 3700.00 with no charges
- **THEN** the holding is 20 units at average cost 3600.00 and total cost 72000.00

### Requirement: Holding valuation
Each holding SHALL show current price with its source and last-updated timestamp, current value in the security currency, and (for USD) the INR equivalent at the latest USD-INR rate with that rate's date. Holdings without any price SHALL show "No price" and no current value.

#### Scenario: US holding in INR
- **WHEN** a user holds 5 AAPL priced 230.00 USD and the latest USD-INR rate is 88.0000
- **THEN** the holding shows 1150.00 USD and 101200.00 INR with the price and rate timestamps

#### Scenario: No price available
- **WHEN** a security has never been priced
- **THEN** its holding shows "No price" and is excluded from current value totals with a count of unpriced holdings

### Requirement: Separate Indian and US views
The Investments section SHALL provide Indian Stocks (all `IN` accounts, INR), US Stocks (all `US` accounts, USD with INR equivalents) and Portfolio Overview (combined, INR).

#### Scenario: US Stocks page
- **WHEN** a user opens US Stocks
- **THEN** only holdings in US accounts are listed with USD values and INR equivalents
