# Spec Delta

## Purpose

Provides FinTrack's consistent, responsive application frame (navigation, layout, theming, design system and shared interaction patterns) that every feature page plugs into.

## ADDED Requirements

### Requirement: Main navigation
The authenticated app SHALL show navigation with: Overview, Transactions, Income, Expenses, Budgets, Savings & Goals, Investments (Indian Stocks, US Stocks, Portfolio Overview), Loans & EMIs (Home Loans, Car Loans, Other Loans), Net Worth, Reports & Analytics, AI Financial Assistant, Settings.

#### Scenario: Navigation present
- **WHEN** a logged-in user opens the app on desktop
- **THEN** all sections above appear in a sidebar with the current section highlighted

### Requirement: Unreleased sections
Sections whose capability is not yet released SHALL be visible but show a "Coming in a later release" state and SHALL NOT call unavailable APIs.

#### Scenario: Budgets in P0
- **WHEN** a P0 user opens Budgets
- **THEN** a coming-soon state is shown and no error appears

### Requirement: Responsive layout
The layout SHALL work from 360 px wide mobile to desktop: below 1024 px the sidebar collapses into a menu drawer, and no page SHALL require horizontal page scrolling (wide tables scroll within their container).

#### Scenario: Mobile
- **WHEN** a user opens Transactions on a 375 px wide screen
- **THEN** navigation is available via a menu button and the page has no horizontal page scroll

### Requirement: Light and dark themes
The app SHALL support light, dark and system themes from the user's preference, applied before first paint, with WCAG AA contrast for text and chart colors in both themes.

#### Scenario: Dark mode
- **WHEN** a user selects dark theme
- **THEN** all pages including charts render in dark theme and the choice persists across sessions

### Requirement: Route protection and session handling
Unauthenticated users SHALL be redirected to login and returned to the original page after login. When the access token expires the app SHALL refresh it silently; when refresh fails it SHALL redirect to login.

#### Scenario: Deep link while logged out
- **WHEN** a logged-out user opens `/transactions`
- **THEN** they are sent to login and then back to `/transactions`

### Requirement: Confirmation for destructive actions
Deleting any financial record, undoing an import or deleting the account SHALL require an explicit confirmation dialog naming what will be deleted.

#### Scenario: Delete transaction
- **WHEN** a user clicks delete on a transaction
- **THEN** a dialog shows the transaction's date, amount and description before deletion

### Requirement: Clear feedback
Successful mutations SHALL show a brief toast; failed ones SHALL show the server's error message and keep the user's input. Form fields SHALL show inline validation errors.

#### Scenario: Server validation error
- **WHEN** the server rejects a transaction form with a field error
- **THEN** the error is shown next to that field and the form values are kept

### Requirement: Accessibility
Interactive elements SHALL be keyboard reachable with visible focus, have accessible names, and charts SHALL provide a tabular or text alternative.

#### Scenario: Keyboard navigation
- **WHEN** a user tabs through the transaction form
- **THEN** every field and button receives visible focus in a logical order
