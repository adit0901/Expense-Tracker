# Tasks: FinTrack P3 – Advanced Features

## 1. Pending transactions and recurring rules

- [ ] 1.1 Add `pending` status, enforce posted-only base query across balances, aggregates, reports, exports and net worth; verify a cross-report test that a pending row changes no figure
- [ ] 1.2 Create `recurring_rules` and `recurring_occurrences` migrations and CRUD/pause/resume/end endpoints; verify integration tests
- [ ] 1.3 Implement recurrence expansion with month-end clamping; verify unit tests for 31 Jan → 28 Feb/31 Mar/30 Apr and interval rules
- [ ] 1.4 Implement daily generation job with backfill, idempotency and no backfill after resume; verify tests for double run, 3-day outage and paused month
- [ ] 1.5 Implement confirm (with edits), skip, income auto-confirm, EMI confirmation via loan payment service, and duplicate check on confirm; verify tests for each spec scenario
- [ ] 1.6 Add recurring to cross-tenant sweep and audit; verify sweep passes

## 2. Notifications

- [ ] 2.1 Create `notifications` and `notification_preferences` migrations, `NotificationService` with uniqueness, center endpoints (list, read, read-all, unread count); verify tests
- [ ] 2.2 Migrate P1 budget alerts to notifications; implement reminder jobs (EMI 3 days ahead, pending occurrences, goal milestones/deadlines, stale prices/FX); verify tests for 2026-12-02 reminder and job re-run uniqueness
- [ ] 2.3 Implement email channel with amount-free templates and per-type preferences; verify a test that rendered emails contain no amounts and Mailpit receives them in E2E

## 3. Insights

- [ ] 3.1 Implement monthly summary, unusual-spending rules, budget and savings suggestions as pure functions; verify unit tests (Shopping spike, insufficient history, 11500.00 suggestion)
- [ ] 3.2 Implement insights persistence, monthly job, on-demand endpoint and dismiss; verify integration tests

## 4. Reports and exports

- [ ] 4.1 Implement report dataset services for the full catalogue; verify each report's totals equal the dashboard/calculation service values in integration tests
- [ ] 4.2 Implement CSV export for all reports with escaping; verify CSV totals equal JSON totals
- [ ] 4.3 Implement PDF rendering (templates, server-side SVG charts, basis notes) in the backend image; verify PDF generation tests and text extraction contains as-of dates
- [ ] 4.4 Implement async export jobs with 7-day expiry and export-ready notification; verify tests

## 5. AI assistant

- [ ] 5.1 Implement `LLMProvider` protocol, Anthropic adapter (config-driven, backend-only key) and a fake provider for tests; verify the app starts and all other tests pass with no provider configured
- [ ] 5.2 Implement consent endpoints and enforcement; verify no provider call occurs without consent
- [ ] 5.3 Implement read-only, session-scoped tools wrapping existing services; verify tests that tools ignore any user id in model arguments
- [ ] 5.4 Implement conversation loop with SSE streaming, labeling instructions, educational notice, figure-verification pass and fallback; verify tests with the fake provider for fabricated-number rejection and net-worth answer matching the API
- [ ] 5.5 Implement conversation storage, deletion, 90-day purge and per-user rate limit; verify tests
- [ ] 5.6 Write `docs/ai-assistant.md` (data sent, consent, tools, limits); verify it lists every tool implemented

## 6. Frontend

- [ ] 6.1 Build recurring rules management and "To confirm" queue (confirm with edit, skip, duplicate warning); verify RTL tests
- [ ] 6.2 Build notification center, header badge and notification preferences in Settings; verify RTL tests
- [ ] 6.3 Build insights panels on Overview and Reports; verify RTL tests for dismiss
- [ ] 6.4 Build full Reports & Analytics catalogue with CSV/PDF export and async export status; verify RTL tests
- [ ] 6.5 Build AI Financial Assistant (not-enabled state, consent screen, streaming chat, fact/assumption/projection labels, figure cards, notice, conversation list/delete); verify RTL tests and that the production bundle contains no LLM key

## 7. Integration verification

- [ ] 7.1 Playwright E2E: create monthly rent rule → occurrence pending → confirm → expense appears once; verify pass
- [ ] 7.2 Playwright E2E with fake LLM provider: consent → ask net worth → answer figure equals Net Worth page; verify pass
- [ ] 7.3 Playwright E2E: export a PDF and a CSV report and compare totals to the screen; verify pass

## Workflow follow-up

- Archive this change after review to complete the FinTrack roadmap baseline.
