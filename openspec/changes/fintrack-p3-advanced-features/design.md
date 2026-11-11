# Design: FinTrack P3 – Advanced Features

## Context

Extends P0–P2 (ledger, calculations layer, worker, net worth, loans simulation, portfolio analytics). See proposal.md for scope and decisions awaiting approval, and this change's specs for requirements.

## Goals / Non-Goals

**Goals:**
- Recurring generation that is idempotent and never posts money movements without confirmation (except opted-in income).
- An assistant whose numbers are provably sourced from existing calculation services.
- Reports whose CSV/PDF output is generated from the same service calls as the UI.

**Non-Goals:**
- Agentic write actions by the assistant, retrieval over free-text documents, fine-tuning, mobile push.

## Decisions

### D1. Tables
| Table | Key columns |
|---|---|
| `recurring_rules` | `user_id`, `template JSONB` (validated by transaction schema), `freq`, `interval`, `by_month_day`, `start_date`, `end_date`, `max_count`, `auto_confirm`, `loan_id NULL`, `goal_id NULL`, `status` (`active`,`paused`,`ended`), `paused_at`, `last_generated_through` |
| `recurring_occurrences` | `rule_id`, `due_date`, `transaction_id NULL`, `state` (`pending`,`confirmed`,`skipped`); unique (`rule_id`,`due_date`) |
| `notifications` | `user_id`, `type`, `subject_key`, `title`, `body`, `link`, `read_at`, `created_at`; unique (`user_id`,`type`,`subject_key`) |
| `notification_preferences` | `user_id`, `type`, `in_app`, `email` |
| `insights` | `user_id`, `period`, `kind`, `payload JSONB`, `dismissed_at`; unique (`user_id`,`period`,`kind`,`subject`) |
| `ai_consents` | `user_id`, `granted_at`, `revoked_at` |
| `ai_conversations` / `ai_messages` | `role`, `content`, `tool_calls JSONB`, `created_at`; purge job deletes > 90 days |
| `export_jobs` | `user_id`, `report`, `format`, `params`, `status`, `storage_key`, `expires_at` |

`transactions.status` gains `pending`; every aggregate query adds `status = 'posted'` (enforced by a shared base query in repositories, with a test asserting it across report endpoints).

### D2. Recurrence engine
Use `dateutil.rrule` for date expansion with month-end clamping (`bymonthday=-1` handling for 29–31). Daily job (00:15 IST) generates occurrences from `last_generated_through + 1` to today for active rules; unique constraint ensures idempotency. Pause stores `paused_at`; resume sets `last_generated_through = resume date − 1` so no backfill. A pending occurrence creates a `transactions` row with `status='pending'` so it shows in lists; confirm flips to `posted` (with optional edits) in one DB transaction; EMI rules call the P1 loan payment service instead.

### D3. AI assistant architecture
`LLMProvider` Protocol; `AnthropicProvider` using the Messages API with tool use; model from config. The backend defines read-only tools mapping 1:1 to existing services: `get_period_summary`, `get_category_breakdown`, `get_net_worth`, `get_budget_status`, `get_loans_summary`, `simulate_prepayment`, `get_portfolio_summary`, `get_goal_progress`, `search_transactions` (limited fields, max 50 rows). Tools receive `user_id` from the authenticated session, never from model output. System prompt: answer only from tool results, label Facts/Assumptions/Projections, include the educational notice, refuse to invent figures. Post-processing verifies every currency figure in the answer appears in tool outputs from that turn (or is derived and labeled projection); unverified figures trigger one regeneration, then a safe fallback message. Free-text user data in tool results is wrapped as data to reduce prompt-injection impact. Streaming responses via SSE. Rate limit via Redis. Logs record token counts and tool names, not content.

### D4. Insights engine
Pure rule functions over calculation outputs (P0–P2), run by the monthly job and on demand; results cached in `insights`. AI, when enabled, may only rephrase an insight's payload.

### D5. Reports and PDF
Each report = one service returning a typed dataset; UI JSON, CSV and PDF render from the same dataset. PDF via HTML templates (Jinja2) rendered with WeasyPrint; charts rendered server-side as SVG. Large exports via `export_jobs` in the worker; files stored with the P0 storage backend and expire after 7 days.

### D6. Notifications
`NotificationService.notify(user, type, subject_key, …)` used by budgets (P1 alerts migrate into notifications), reminders job (EMIs, recurring), goals, market-data staleness, insights, exports. Email via existing SMTP adapter with amount-free templates; uniqueness by (`type`,`subject_key`).

## Risks / Trade-offs

- [LLM states wrong numbers despite tools] → figure-verification pass + fallback; UI shows tool-derived figure cards beside text.
- [Prompt injection via transaction text] → tools are read-only and user-scoped; data wrapped and delimited; no tool can reach other users.
- [Privacy of sending data to a third party] → explicit consent, minimal tool outputs, no account numbers/receipts, provider data-retention settings documented.
- [LLM cost] → per-user rate limits, max tokens, conversation length cap.
- [WeasyPrint system dependencies] → bundled in backend Docker image; PDF tests in CI.
- [Pending rows leaking into aggregates] → single posted-only base query + cross-report test.

## Migration Plan

Forward migrations for new tables and `status` enum value; P1 `budget_alerts` backfilled into `notifications`. LLM disabled unless configured. Rollback: disable jobs, downgrade (refuses if pending transactions exist unless they are skipped first).

## Open Questions

- Default model and token budgets per message — tunable configuration, no spec impact.
