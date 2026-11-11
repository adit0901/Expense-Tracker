# Spec Delta

## Purpose

Explains how a user's investments are performing: invested amount, current value, realized and unrealized returns, dividends, allocation across markets and sectors, and how much of US returns came from the stock versus the rupee-dollar rate.

## ADDED Requirements

### Requirement: Portfolio summary
For a portfolio scope (Indian, US, or combined) the system SHALL show: invested amount (cost basis of current holdings), current value, unrealized P/L = current value − invested amount, unrealized return % = unrealized P/L ÷ invested amount × 100, realized P/L for a selected period, and dividend income (net) for the period. Unpriced holdings SHALL be excluded from these figures and counted separately.

#### Scenario: Summary
- **WHEN** invested amount is 500000.00 and current value is 575000.00
- **THEN** unrealized P/L is 75000.00 and return is 15.00%

#### Scenario: Zero invested
- **WHEN** a scope has no current holdings
- **THEN** return % is null and shown "—"

### Requirement: Per-holding performance
The system SHALL list each holding with quantity, average cost, current price, invested, current value, unrealized P/L amount and %, day change when available, and share of the portfolio, sortable by each column.

#### Scenario: Top gainer
- **WHEN** a user sorts by unrealized return descending
- **THEN** holdings are ordered by unrealized P/L %

### Requirement: Currency vs price gain for USD holdings
For USD holdings, total INR unrealized gain SHALL be split into price gain = Q × (P1 − P0) × FX1 and currency gain = Q × P0 × (FX1 − FX0), where Q is quantity, P0 average cost (USD), P1 current price (USD), FX0 = INR cost basis ÷ USD cost basis, and FX1 the current rate. The two SHALL sum exactly to the total INR gain.

#### Scenario: Attribution
- **WHEN** 10 AAPL have USD cost 2000.00, INR cost 166000.00, price 230.00 and rate 88.0000
- **THEN** total INR gain is 36400.00, price gain 26400.00 and currency gain 10000.00

### Requirement: Allocation
The system SHALL show allocation of current value (INR) by market (India vs US), by security type, by sector (with "Unclassified" when sector is unknown) and by holding.

#### Scenario: India vs US
- **WHEN** Indian holdings are worth 600000.00 and US holdings 400000.00 (INR)
- **THEN** allocation is India 60.00% and US 40.00%

### Requirement: Dividend income report
The system SHALL report dividends by month, security and market with gross, tax withheld and net, in original currency and INR.

#### Scenario: Annual dividends
- **WHEN** a user views FY 2026-27 dividends
- **THEN** totals per security and the FY total in INR are shown

### Requirement: Portfolio value history
The system SHALL show portfolio value history using stored daily closing prices and FX rates where available, marking periods without price data rather than filling them.

#### Scenario: Gaps in history
- **WHEN** prices are missing for a week
- **THEN** the chart shows a gap for that week
