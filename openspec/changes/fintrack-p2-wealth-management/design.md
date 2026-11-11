# Design: FinTrack P2 – Wealth Management

## Context

Extends P0 architecture and P1's worker (Redis + ARQ) and net worth engine (`investment_value_provider` hook). See proposal.md for scope and decisions awaiting approval, and this change's specs for requirements.

## Goals / Non-Goals

**Goals:**
- Holdings and realized P/L recomputed deterministically from an ordered investment transaction log.
- External data (prices, FX) isolated behind adapters with provenance on every value.
- Correct INR conversion with reproducible historical values.

**Non-Goals:**
- Tax lots/FIFO, tax reporting, intraday streaming, derivatives, mutual fund NAV feeds.

## Decisions

### D1. Tables
| Table | Key columns |
|---|---|
| `investment_accounts` | `user_id`, `name`, `broker`, `market` (`IN`/`US`), `currency`, `closed_at` |
| `securities` | `exchange`, `symbol`, `name`, `type`, `currency`, `isin`, `sector`, `provider_ref`, `owner_user_id NULL` (non-null = user-created manual security); unique (`exchange`,`symbol`,`owner_user_id`) |
| `investment_transactions` | `user_id`, `account_id`, `security_id`, `type` (`buy`,`sell`,`dividend`,`split`,`bonus`), `trade_date`, `quantity NUMERIC(20,8)`, `price NUMERIC(20,8)`, `charges JSONB` + `charges_total`, `gross`, `tax_withheld`, `ratio_num`, `ratio_den`, `fx_rate NUMERIC(18,8) NULL`, `inr_amount NUMERIC(19,4)`, `ledger_transaction_id NULL` |
| `holdings` | derived cache: `account_id`, `security_id`, `quantity`, `cost_ccy`, `cost_inr`, `realized_pl_ccy`, `realized_pl_inr`, `version`; rebuilt on any change to that (account, security) |
| `market_prices` | `security_id`, `price_date`, `price_ts`, `close`, `source`, `retrieved_at`, `user_id NULL` (manual) ; unique (`security_id`,`price_date`,`source`,`user_id`) |
| `exchange_rates` | `base`='USD', `quote`='INR', `rate_date`, `rate NUMERIC(18,8)`, `source`, `retrieved_at`, `user_id NULL` (manual) |

### D2. Holdings engine
`replay(transactions_sorted)` pure function: iterate by (`trade_date`, sequence); buy adds cost (ccy and INR via trade's rate); sell removes `avg × qty` from both currencies and accrues realized P/L in ccy and INR (INR realized uses sale-date rate for proceeds and INR average cost for cost); split/bonus scale quantity; dividend accrues income only. Validation fails if quantity < 0 at any step. Results cached in `holdings` keyed by version; any write to that pair triggers replay inside the same DB transaction. *Alternative*: incremental updates — rejected, edits/deletes of past trades make incremental state error-prone.

### D3. FX attribution
FX0 = `cost_inr ÷ cost_ccy` (weighted historical rate), giving exact decomposition of unrealized INR gain into price and currency parts (spec formula). Implemented in calculations layer with Decimal; tested for exact sum.

### D4. Market data adapters
`MarketDataProvider` Protocol: `search(query, market)`, `quotes(securities)`, `history(security, start, end)`, `limits()`. Implementations: `ManualProvider` (no-op), `TwelveDataProvider` (if approved), `FakeProvider` for tests. A `PriceService` resolves "latest price for user" = max timestamp across provider prices and that user's manual prices. Refresh jobs: per market session schedule (NSE 09:15–15:30 IST, US 09:30–16:00 ET with DST via `zoneinfo`), market holiday calendars as config data. Rate limiting: token bucket in Redis per provider; batches per provider's max symbols; 429 → exponential back-off job requeue. Quotes cached in Redis (TTL 15 min) and persisted daily closes in `market_prices`.

### D5. FX adapters
`FxProvider` Protocol with `EcbFxProvider` (daily reference rates via a public ECB-based API; USD-INR derived from EUR cross rates, stored with source `ecb`) and manual entry. Daily job at 18:30 CET-equivalent; conversion lookup = latest rate ≤ date.

### D6. Ledger linkage
When a trade/dividend is linked to a bank account, the investments service creates the P0 ledger row (`investment_buy`/`investment_sell`/`dividend`) in the same DB transaction and stores `ledger_transaction_id`; edits propagate; deleting the investment transaction deletes the ledger row. Manual income entries in the "Dividends" category remain possible; UI warns when a manual Dividends entry matches a recorded investment dividend (amount/date) to avoid double counting.

### D7. Net worth hook
Register `InvestmentValueProvider` implementing P1's hook: Σ holdings value as of date (price ≤ date, FX ≤ date), unpriced at INR cost with label. Snapshot breakdown gains `indian_stocks`, `us_stocks`.

### D8. API
`/investment-accounts`, `/securities/search?q=&market=`, `POST /securities` (manual), `/investment-transactions` (CRUD + filters + export.csv), `/holdings?market=`, `/portfolio/summary?scope=&period=`, `/portfolio/allocation`, `/portfolio/history`, `/portfolio/dividends`, `/prices/{security_id}` (history), `POST /prices/manual`, `POST /prices/refresh`, `/fx/usd-inr?date=`, `POST /fx/usd-inr/manual`.

### D9. Frontend
Investments section with sub-routes Indian Stocks, US Stocks, Portfolio Overview; holdings table (sortable, sticky header), trade form with itemized charges and FX rate field (pre-filled with reference rate, editable), corporate action dialog, price freshness badges (`Live`, `Close`, `Stale`, `Manual`, `No price`), attribution card for US gains.

## Risks / Trade-offs

- [Provider licensing/cost; unofficial NSE APIs] → manual-first, adapter only after approval; never scrape.
- [ECB rate differs from bank remittance rate] → user-entered trade rate overrides; label sources.
- [Average cost differs from broker's FIFO P/L] → explicit label "Average-cost basis; not a tax computation".
- [Corporate actions entered late] → replay recomputes history; realized P/L of later sells adjusts automatically.
- [Holiday calendars drift] → calendar data file versioned in repo with yearly update task; staleness rule tolerant by one trading day.

## Migration Plan

New tables and ledger enum values (`investment_buy`, `investment_sell`, `dividend`) via forward migrations; provider config off by default. Rollback: disable jobs, downgrade migrations (refuses if ledger rows of new types exist unless removed).

## Open Questions

- Which provider plan to purchase (if any) once licensing is confirmed — adapter-level only.
