# Proposal: FinTrack P2 – Wealth Management

## Why

Many FinTrack users invest in both Indian (NSE/BSE) and US markets, and their real wealth and returns are invisible without tracking holdings, cost basis, prices and the USD-INR rate. P2 adds investment portfolios with correct cost-basis accounting, market and FX data that is never fabricated, and analytics that separate stock performance from currency movement. Depends on P0 and P1 being implemented and archived.

## What Changes

- Investment accounts (Indian demat/broker, US broker) and a securities master for NSE/BSE stocks and US stocks/ETFs.
- Investment transactions: buy, sell (incl. partial), dividend (gross, tax withheld, net), stock split, bonus issue, brokerage and charges; holdings derived from transaction history.
- Weighted-average cost basis, realized and unrealized profit/loss, dividend income.
- Market data abstraction with provider adapters, caching, rate-limit handling, last-updated timestamps, manual prices, and an explicit "no price" state — prices are never invented.
- USD-INR exchange rates with daily history, manual entry, original-currency and INR display, and separation of currency gain from price gain.
- Portfolio analytics: invested vs current value, absolute and % returns, India vs US allocation, sector allocation, per-holding performance, dividend income.
- Ledger integration: new transaction types `investment_buy`, `investment_sell`, `dividend` so bank balances stay correct without counting purchases as expenses.
- Net worth includes investment holdings (INR); dashboard gains investment tiles and allocation charts.

## Capabilities

### New Capabilities
- `investment-portfolio`: investment accounts, securities, derived holdings and their valuation.
- `investment-transactions`: trade, dividend and corporate-action records and cost-basis rules.
- `market-data`: security prices from providers or manual entry, with caching and freshness.
- `currency-exchange`: USD-INR rates, history and conversion rules.
- `portfolio-analytics`: returns, allocation, performance and FX-vs-price gain attribution.

### Modified Capabilities
Introduced in earlier changes; this change only ADDS requirements:
- `transactions`: investment ledger types.
- `net-worth`: includes investment holdings.
- `dashboard-overview`: investment tiles and allocation.

## Impact

- Backend domains `investments`, `marketdata`, `fx`; integrations `integrations/marketdata/*`, `integrations/fx/*`; worker jobs for price/FX refresh.
- Config: optional provider API keys (`MARKET_DATA_PROVIDER`, `MARKET_DATA_API_KEY`); without them the app runs in manual-price mode.
- Frontend: Investments section (Indian Stocks, US Stocks, Portfolio Overview).

## Decisions Requiring Approval

1. **Cost basis = weighted-average cost** (buy charges included). Realized P/L on sell = net sale proceeds − average cost × quantity sold. FIFO (the Indian capital-gains tax rule) is not used; FinTrack's figures are not tax computations.
2. **Brokerage, STT, exchange/SEBI fees, stamp duty and GST on buys are added to cost basis; on sells they reduce proceeds.** They are not counted as expenses.
3. **Market data provider**: ship manual prices plus one pluggable adapter. Recommended: Twelve Data (covers NSE, BSE and US in one API) — licensing and plan costs to be confirmed before enabling; no scraping of NSE/BSE websites.
4. **FX source**: daily USD-INR from the ECB reference rate (via a free API) plus manual entry; RBI reference rate can be added as an adapter. Trades use the user-entered rate if given (actual remittance rate), otherwise the reference rate for the trade date.
5. **Unpriced holdings** (no price ever obtained): excluded from current-value and return figures and flagged; included in net worth at cost and labeled "valued at cost".
6. **Broker cash balances are not modeled**: buys/sells can optionally link to a bank account (creating `investment_buy`/`investment_sell` ledger entries); otherwise only the investment ledger changes.

## Out of Scope (P2)

Mutual fund NAV automation (MFs remain manual assets from P1), options/futures, crypto, broker statement/CAS import, tax reports (STCG/LTCG, Schedule FA), real-time streaming prices, corporate actions other than split, bonus and cash dividend (no mergers, rights or spin-offs).
