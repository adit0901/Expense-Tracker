# Spec Delta

## Purpose

Tells users about things that need their attention — budget alerts, due EMIs and recurring items, goal milestones, stale data and monthly summaries — through an in-app notification center and optional email, under their control.

## ADDED Requirements

### Requirement: Notification center
The app SHALL provide a notification center listing notifications newest first with read/unread state, mark-as-read, mark-all-read and an unread badge in the header.

#### Scenario: Unread badge
- **WHEN** a user has 3 unread notifications
- **THEN** the header badge shows 3

### Requirement: Notification types
The system SHALL notify for: budget threshold alerts, EMI due in 3 days, pending recurring occurrences to confirm, goal milestones (25/50/75/100%), goal deadline approaching, stale prices or missing FX rate affecting the portfolio, monthly summary ready, and export ready.

#### Scenario: EMI reminder
- **WHEN** an EMI is due on 2026-12-05
- **THEN** a reminder notification is created on 2026-12-02

### Requirement: Channels and preferences
Users SHALL choose per notification type whether to receive it in-app (default on) and by email (default off except monthly summary). Emails SHALL NOT contain amounts, balances or account details — only a description and a link into the app.

#### Scenario: Email content
- **WHEN** a budget alert email is sent
- **THEN** it says a budget needs attention and links to Budgets without stating amounts

### Requirement: No duplicate notifications
The system SHALL send each notification at most once per subject and period (for example one 80% alert per budget per month, one reminder per EMI installment).

#### Scenario: Re-run reminders
- **WHEN** the reminder job runs twice on the same day
- **THEN** only one reminder exists per installment
