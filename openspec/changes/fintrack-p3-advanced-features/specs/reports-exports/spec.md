# Spec Delta

## Purpose

Provides the complete catalogue of FinTrack reports across income, spending, planning, net worth, investments and loans, each exportable as CSV and PDF with figures identical to the app.

## ADDED Requirements

### Requirement: Report catalogue
Reports & Analytics SHALL offer: income (monthly/annual), expenses (by category, payment method), savings rate trend, budget utilization, net worth history, investment performance, realized and unrealized gains, dividend income, loans and EMIs (outstanding, interest paid), and goal progress, each with period filters including financial year.

#### Scenario: Loans report
- **WHEN** a user opens the loans report for FY 2026-27
- **THEN** it shows per-loan principal and interest paid in the FY and outstanding at FY end

### Requirement: CSV export
Every report SHALL be exportable as CSV with the same rows and totals as displayed, decimals as plain strings, and formula-injection escaping.

#### Scenario: Same figures
- **WHEN** a user exports the expense report
- **THEN** the CSV totals equal the on-screen totals

### Requirement: PDF export
Every report SHALL be exportable as a PDF containing the title, user's name, period, generation timestamp, tables, charts and the calculation-basis notes (for example "average-cost basis", price and FX dates).

#### Scenario: PDF content
- **WHEN** a user exports the investment performance PDF
- **THEN** the PDF lists holdings with prices' as-of dates and the cost-basis note

### Requirement: Large exports run asynchronously
Exports estimated above 10,000 rows or any PDF over 20 pages SHALL be generated in the background, with the user notified when ready and the file available for 7 days.

#### Scenario: Large export
- **WHEN** a user exports 5 years of transactions
- **THEN** they are told the export is being prepared and receive a notification with a download link when done
