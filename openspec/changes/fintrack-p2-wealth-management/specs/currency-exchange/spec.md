# Spec Delta

## Purpose

Converts USD amounts (US investments and dividends) to INR, FinTrack's reporting currency, using a recorded history of USD-INR rates so every converted figure is reproducible and shows both currencies.

## ADDED Requirements

### Requirement: USD-INR rate history
The system SHALL store daily USD-INR rates with date, rate (up to 4 decimals shown, 8 stored), source (provider or `manual`) and retrieval time, fetched daily when a provider is configured. Users SHALL be able to enter a rate manually for any date.

#### Scenario: Daily fetch
- **WHEN** the daily FX job runs on 2026-11-11
- **THEN** a USD-INR rate dated 2026-11-11 (or the latest published date) is stored with its source

### Requirement: Rate selection for conversions
Conversion for a date SHALL use the rate for that date, or the most recent earlier rate if none exists for that date (labeled with its actual date). For trades and dividends, a user-entered transaction rate SHALL take precedence.

#### Scenario: Holiday
- **WHEN** a dividend is paid on a date with no published rate
- **THEN** the previous available rate is used and its date is shown

#### Scenario: User remittance rate
- **WHEN** a user enters 88.25 as the rate on a USD buy
- **THEN** that buy's INR cost uses 88.25, not the reference rate

### Requirement: Dual-currency display
Every USD amount in the UI and exports SHALL be shown with its INR equivalent and the rate date used; aggregates SHALL be reported in INR.

#### Scenario: Dividend display
- **WHEN** a 7.50 USD net dividend is shown and the rate used is 87.0000 of 2026-10-15
- **THEN** it displays 7.50 USD (₹652.50 at 87.0000 on 15 Oct 2026)

### Requirement: Historical conversion snapshots
INR values recorded at transaction time (INR cost basis of buys, INR value of dividends) SHALL be stored and SHALL NOT change when later rates arrive.

#### Scenario: Cost basis stable
- **WHEN** a buy's INR cost was recorded at 83.0000 and today's rate is 88.0000
- **THEN** the INR cost basis remains computed at 83.0000

### Requirement: Missing rate
When no USD-INR rate has ever been recorded, USD amounts SHALL be shown in USD only with "INR value unavailable", and INR aggregates SHALL exclude them with a visible notice.

#### Scenario: Fresh install without provider
- **WHEN** a user has US holdings and no rates
- **THEN** Portfolio Overview shows a notice prompting a manual USD-INR rate entry
