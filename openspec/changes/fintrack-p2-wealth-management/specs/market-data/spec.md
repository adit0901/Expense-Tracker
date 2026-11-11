# Spec Delta

## Purpose

Supplies current and historical security prices from pluggable providers or manual entry, with caching, rate-limit handling and visible freshness, guaranteeing FinTrack never shows a price that did not come from a provider or the user.

## ADDED Requirements

### Requirement: Provider-agnostic price sources
The system SHALL obtain prices through a provider abstraction supporting security search, latest quote and daily historical closes, configurable per market (IN, US). The application SHALL work fully with no provider configured.

#### Scenario: No provider configured
- **WHEN** the system runs without market data configuration
- **THEN** investments work with manual prices and the UI states that automatic prices are disabled

### Requirement: Prices are never fabricated
Every stored price SHALL carry its source (provider name or `manual`), the price timestamp, and retrieval time. The system SHALL NOT interpolate, estimate or carry forward prices without labeling them; when no price exists it SHALL report "No price".

#### Scenario: Provider error
- **WHEN** the provider fails for a security that has a price from 3 days ago
- **THEN** the system shows the 3-day-old price with its timestamp and a stale indicator, not a new price

### Requirement: Manual price entry
A user SHALL be able to enter a price for a security and date; manual prices SHALL apply only to that user's valuations and SHALL be labeled "Manual".

#### Scenario: Manual price used
- **WHEN** a user enters 1520.00 for INFY on 2026-11-11
- **THEN** their INFY holding is valued at 1520.00 labeled "Manual, 11 Nov 2026"

#### Scenario: Newer provider price
- **WHEN** a provider price with a later timestamp than the manual price arrives
- **THEN** valuations use the newer provider price and the manual price is kept in history

### Requirement: Caching and refresh
Latest quotes SHALL be cached and refreshed on a schedule (default every 15 minutes during each market's trading hours, and once after close) and on user request no more than once per minute per user. Responses SHALL include `last_updated` for each price.

#### Scenario: Refresh throttled
- **WHEN** a user clicks refresh twice within a minute
- **THEN** the second request returns cached prices with their timestamps

### Requirement: Provider rate limits
The system SHALL respect provider rate limits by batching requests and queueing excess requests; when a limit is hit it SHALL back off and retry later, never failing user page loads because of it.

#### Scenario: Limit exceeded
- **WHEN** the provider responds with a rate-limit error during a scheduled refresh
- **THEN** remaining securities are retried after the provider's back-off period and pages continue to show cached prices

### Requirement: Staleness indication
A price SHALL be marked stale when older than one trading day for its market (or older than 15 minutes during trading hours when live refresh is enabled).

#### Scenario: Weekend
- **WHEN** a user views US holdings on a Sunday with Friday's closing prices
- **THEN** prices are not marked stale
