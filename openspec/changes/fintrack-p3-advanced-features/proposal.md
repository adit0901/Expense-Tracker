# Proposal: FinTrack P3 – Advanced Features

## Why

With tracking, planning and investments in place, the remaining friction is repetitive data entry and turning data into understanding. P3 reduces entry effort with recurring transactions, adds an AI financial assistant and rule-based insights grounded in the user's own deterministic figures, delivers complete CSV/PDF reports, and notifies users of what needs attention. Depends on P0–P2 being implemented and archived.

## What Changes

- Recurring rules (daily, weekly, monthly, yearly) for salary, rent, subscriptions, SIPs, insurance premiums and EMIs, with start/end dates, pause/resume, and generation of **pending** occurrences that the user confirms (salary-type rules may opt into auto-confirm). Idempotent generation prevents duplicates.
- AI Financial Assistant: chat that answers questions about the authenticated user's finances using backend tools that return deterministic figures; responses label facts, assumptions and projections and carry an educational-use disclaimer; requires explicit consent; the app works fully without an AI provider configured.
- Financial insights: rule-based monthly summary, unusual-spending detection, budget and savings suggestions — available without AI; AI may phrase them when enabled.
- Reports & Analytics: full report catalogue (income, expenses, savings trend, budget utilization, net worth history, investment performance, realized/unrealized gains, dividends, loans/EMIs, goals) with CSV and PDF export.
- Notifications: in-app notification center plus optional email for budget alerts, EMI/recurring due reminders, goal milestones, stale-price warnings and monthly summaries, with per-type preferences.

## Capabilities

### New Capabilities
- `recurring-transactions`: recurring rules and their pending occurrences.
- `ai-assistant`: LLM-powered Q&A over the user's own financial data.
- `financial-insights`: deterministic analyses and recommendations.
- `reports-exports`: report catalogue and CSV/PDF export.
- `notifications`: notification center, channels and preferences.

### Modified Capabilities
Introduced in earlier changes; this change only ADDS requirements:
- `transactions`: pending status for occurrences awaiting confirmation.

## Impact

- Backend domains `recurring`, `assistant`, `insights`, `reports`, `notifications`; integrations `integrations/llm/*`, PDF rendering; worker jobs for occurrence generation, reminders and monthly summaries.
- Config: optional `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL` (backend only); SMTP for email notifications.
- Frontend: AI Financial Assistant page, notification center, recurring management, full Reports & Analytics.

## Decisions Requiring Approval

1. **LLM provider**: Anthropic Claude (Messages API with tool use) behind a provider interface; default model configurable (`claude-sonnet-5-5` suggested). Other providers can be added as adapters.
2. **Data sent to the LLM**: only the results of tool calls needed for the question (aggregates and the specific rows asked about), never credentials, account numbers or receipts; requires a one-time opt-in with a plain-language explanation, revocable in Settings. Conversations are stored for 90 days and deletable.
3. **Recurring occurrences are pending by default**; only income rules may enable auto-confirm. EMI rules link to P1 loans and confirm through the loan payment flow.
4. **PDF generation server-side** (HTML templates rendered to PDF) to keep figures identical to the API.
5. **Insights are rule-based first**; AI is optional phrasing, never the source of a number.

## Out of Scope (P3)

Bank/SMS/email transaction auto-capture, push notifications to mobile devices, AI that executes changes (assistant is read-only), personalized investment or tax advice, scheduled report emailing beyond the monthly summary.
