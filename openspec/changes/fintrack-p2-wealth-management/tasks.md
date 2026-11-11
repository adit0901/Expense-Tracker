# Tasks: FinTrack P2 – Wealth Management

## 1. Data model

- [ ] 1.1 Create migrations for `investment_accounts`, `securities`, `investment_transactions`, `holdings`, `market_prices`, `exchange_rates` and ledger enum values `investment_buy`, `investment_sell`, `dividend`; verify migration up/down in CI

## 2. Calculations

- [ ] 2.1 Implement holdings `replay` (buy, sell, dividend, split, bonus; ccy and INR; negative-quantity guard); verify table-driven tests for every investment-transactions scenario (35020.00/3502.00, 1177.00, 3541.20, 700.40, 350.20)
- [ ] 2.2 Implement portfolio summary, return %, allocation and FX attribution; verify the AAPL test (36400.00 = 26400.00 + 10000.00) and null return on zero invested
- [ ] 2.3 Extend `docs/financial-calculations.md` with cost basis, realized/unrealized P/L, FX attribution and conversion rules; verify examples map to tests

## 3. FX

- [ ] 3.1 Implement `FxProvider` protocol, ECB adapter, manual entry, lookup (latest ≤ date) and daily job; verify tests with a fake provider for holiday fallback and user-rate precedence
- [ ] 3.2 Implement missing-rate behavior (USD-only display, aggregates exclusion notice); verify API tests

## 4. Market data

- [ ] 4.1 Implement `MarketDataProvider` protocol, `ManualProvider`, `FakeProvider`, `PriceService` (latest of provider/manual) with provenance; verify tests for manual vs newer provider price and "No price"
- [ ] 4.2 Implement refresh jobs with market sessions/holiday calendars, Redis token-bucket rate limiting, back-off requeue and per-user refresh throttle; verify tests with fake provider returning 429 and weekend staleness
- [ ] 4.3 Implement the approved real provider adapter behind config (only after licensing decision); verify a contract test using recorded responses

## 5. Investments API

- [ ] 5.1 Implement investment accounts and securities (search, manual create, exchange/currency validation); verify tests incl. RELIANCE on NSE vs BSE and US-account restriction
- [ ] 5.2 Implement investment transaction CRUD with replay in the same DB transaction, oversell 422, delete-conflict 409, history filters and CSV export; verify integration tests
- [ ] 5.3 Implement ledger linkage for funded buys, sale proceeds and dividends; verify bank balance and income/expense tests from the transactions delta
- [ ] 5.4 Implement holdings, portfolio summary/allocation/history/dividends endpoints; verify integration tests incl. unpriced exclusion counts
- [ ] 5.5 Add investments, prices (manual) and FX (manual) to cross-tenant sweep and audit; verify sweep passes

## 6. Net worth and dashboard

- [ ] 6.1 Register `InvestmentValueProvider` for net worth and snapshots, add breakdown keys, block `stocks` manual asset type; verify tests for 1670000.00 and "valued at cost"
- [ ] 6.2 Extend dashboard overview with investment tile, allocation and "prices as of"; verify integration test

## 7. Frontend

- [ ] 7.1 Build Indian Stocks and US Stocks pages (holdings table, freshness badges, INR equivalents with rate date); verify RTL tests
- [ ] 7.2 Build trade, dividend and corporate-action forms (itemized charges, FX rate prefill, validation messages); verify RTL tests for fractional IN rejection and oversell error
- [ ] 7.3 Build Portfolio Overview (summary, allocation charts, history with gaps, dividends report, FX attribution card); verify RTL tests
- [ ] 7.4 Build manual price and manual FX entry dialogs and provider-disabled notices; verify RTL tests

## 8. Integration verification

- [ ] 8.1 Playwright E2E with no provider: add US account → manual FX rate → buy AAPL → manual price → Portfolio Overview and net worth reflect INR value with labels; verify pass
- [ ] 8.2 Playwright E2E: buy, partial sell, split, dividend on an Indian stock → realized P/L and holdings match the spec examples; verify pass

## Workflow follow-up

- Archive this change after review, before starting `fintrack-p3-advanced-features`.
