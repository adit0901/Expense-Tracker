# Financial calculations

This document is the reference for every figure FinTrack shows. All formulas are implemented
once, in `backend/app/services/calculations/` (pure functions over `Decimal`), and reused by the
dashboard, reports, CSV exports and (from P3) the AI assistant. The frontend only formats the
strings it receives and never recomputes totals.

Each worked example below is mirrored by an automated test; the **Test** line names it
(`backend/tests/unit/test_calculations.py` unless another file is given).

## Conventions

| Rule | Detail |
|---|---|
| Arithmetic | `decimal.Decimal`, precision 28, `ROUND_HALF_UP`. Never binary floats. |
| Stored precision | Amounts are entered with at most 2 decimal places (INR); columns are `NUMERIC(19,4)`. |
| Rounding | Intermediate results keep full precision; final money figures and percentages are rounded half-up to 2 dp only when produced. |
| Sign | Amounts are always positive. Direction comes from the transaction type, never the sign. |
| Reporting currency | INR. |
| Serialization | Money and percentages are JSON strings (`"1250.50"`); "not applicable" is `null` (shown as "N/A" or "—"). |

## What counts as income and expense

| Transaction type | Income | Expenses | Notes |
|---|---|---|---|
| `income` | ✔ (net amount credited) | | Salary gross and deductions are reported separately, never as expenses. |
| `expense` | | ✔ (+) | Credit-card purchases count on the purchase date. |
| `refund` | | ✔ (−) | Reduces its category's expenses in the month the refund is dated. |
| `transfer` | | | Includes credit-card bill payments; moves money between own accounts. |
| P1+ `loan_payment`, `investment_buy`/`sell` | | | Excluded (only loan **interest** is an expense, via the "Loan Interest" category). |

---

## F1. Monthly Income

**Definition.** `Income = Σ amount of income transactions dated in the period`.

**Example.** A month has income 80,000.00, a transfer of 20,000.00 and an expense of 100.00.
Income = **80,000.00**. Transfers and expenses are ignored.

**Test:** `test_fc02_income_counts_only_income_transactions`.

**Salary at net.** A salary with gross 150,000.00 and deductions TDS 25,000.00, EPF 1,800.00
and Professional Tax 200.00 is credited at **123,000.00**. That is the income figure. The
25,000.00 TDS is not an expense.

**Tests:** `tests/integration/test_income.py::test_valid_salary_breakdown`,
`::test_tds_is_not_an_expense`.

## F2. Salary breakdown consistency

**Definition.** `Net = Gross − Σ deductions`, and `Net` must equal the transaction amount.
Otherwise the API responds 422 `salary_breakdown_mismatch`.

**Example.** 150,000.00 − (25,000.00 + 1,800.00 + 200.00) = **123,000.00**. Entering
125,000.00 as the credited amount is rejected.

**Tests:** `tests/integration/test_income.py::test_valid_salary_breakdown`,
`::test_salary_breakdown_mismatch`.

## F3. Monthly Expenses

**Definition.** `Expenses = Σ expense − Σ refund`, over transactions dated in the period.

**Example (refund).** A Shopping expense of 3,000.00 and a Shopping refund of 1,000.00 in the
same month give expenses of **2,000.00**.

**Test:** `test_fc03_expenses_are_net_of_refunds`.

**Example (credit card).** A card purchase of 15,000.00 and the 15,000.00 bill payment (a
transfer) in the same month give expenses of **15,000.00**, counted once.

**Tests:** `test_fc04_card_purchase_and_bill_payment_counted_once` and
`tests/integration/test_dashboard.py::test_card_purchase_and_bill_same_month_counted_once`.

**Example (decimals).** Expenses of 0.10 + 0.20 + 0.30 total exactly **0.60**.

**Test:** `test_fc01_decimal_sum_no_float_drift`.

## F4. Monthly Savings

**Definition.** `Savings = Income − Expenses`. Savings may be negative.

**Example.** Income 80,000.00 and expenses 95,000.00 give savings of **−15,000.00**.

**Test:** `test_fc05_overspending_gives_negative_savings`.

## F5. Savings Rate

**Definition.** `Savings Rate = Savings ÷ Income × 100`, rounded half-up to 2 dp. When
income is 0 the rate is **null** (N/A), never 0, infinity or an error.

**Example.** Income 120,000.00 and expenses 90,000.00 give savings of 30,000.00 and a rate of
**25.00**.

**Test:** `test_fc06_savings_rate`.

**Example (zero income).** Income 0 and expenses 5,000.00 give savings of −5,000.00 and a rate
of **null**.

**Test:** `test_fc07_zero_income_rate_is_null`.

**Example (rounding).** Savings 1 on income 3 gives **33.33**. Savings 2 on income 3 gives
**66.67**. Savings −1 on income 8 gives **−12.50**.

**Test:** `test_fc08_rate_rounds_half_up_to_2dp`.

## F6. Category totals and shares

**Definition.** A category's total is the net expense (expense − refund) of the category
**and its subcategories**. `Share = Category total ÷ Total expenses × 100`. When total
expenses are 0, shares are null.

**Example.** Food is 15,000.00 of 60,000.00, so Food's share is **25.00**. Rent at 45,000.00
has a share of **75.00**.

**Test:** `test_fc09_category_share`.

**Example (roll-up).** A Groceries purchase (a subcategory of Food) of 50.00 adds to Food's
total.

**Tests:** `tests/integration/test_dashboard.py::test_category_breakdown_top6_plus_other` and
`tests/integration/test_transactions.py::test_filter_food_in_october_includes_subcategories`.

**Dashboard donut.** The donut shows the 6 largest top-level categories, and the rest are
summed into "Other categories".

**Test:** `test_fc13_top_six_plus_other`.

## F7. Period boundaries

Periods are calendar based in the user's time zone (default Asia/Kolkata). A transaction
belongs to a period by its **transaction date**, not its entry time. All ranges are inclusive.

| Period | Range | Example |
|---|---|---|
| Month | 1st to last day of the month | Nov 2026 = 2026-11-01 to 2026-11-30 |
| Quarter | Jan–Mar, Apr–Jun, Jul–Sep, Oct–Dec | Q4 2026 = 2026-10-01 to 2026-12-31 |
| Calendar year | 1 Jan to 31 Dec | 2026 |
| Indian financial year | 1 Apr to 31 Mar | **FY 2026-27 = 2026-04-01 to 2027-03-31** |
| Custom | Inclusive start and end | 2026-07-15 to 2026-09-15 (63 days) |

**Tests:** `test_fc10_financial_year`, `test_resolve_period`,
`test_custom_period_inclusive_and_validation`, and
`tests/integration/test_dashboard.py::test_financial_year_filter`.

**Example (back-dated).** A transaction dated 2026-10-31 and entered on 2026-11-02 counts toward
**October 2026**.

**Tests:** `test_fc11_back_dated_entry_belongs_to_txn_month` and
`tests/integration/test_dashboard.py::test_november_vs_october`.

## F8. Change versus the previous period

**Definition.** The previous equivalent period has the same granularity and immediately
precedes the current one: the previous month, quarter, year or FY. For a custom range it is
the same number of days immediately before.

`Change % = (Current − Previous) ÷ |Previous| × 100`. When the previous value is 0 the change
is null and is displayed as "—".

The savings-rate tile reports the difference in percentage **points**.

**Example.** Income of 110 against 100 is **+10.00 %**. Income of 100 against 0 is **null**.

**Tests:** `test_fc12_percent_change` and `test_previous_period`.

**Example (dashboard).** Income of 120,000.00 in November 2026 against 100,000.00 in October
is **+20.00 %**. A savings rate of 25.00 against 39.50 is **−14.50 points**.

**Test:** `tests/integration/test_dashboard.py::test_november_vs_october`.

## F9. Account balances

**Definition.** `Balance = Opening balance + Σ signed effect of posted transactions dated on
or after the opening date`. A balance is never stored as an editable field. Sign rules live in
`services/calculations/balances.py`:

| Type | Source account (asset) | Destination account (asset) |
|---|---|---|
| income | + | — |
| expense | − | — |
| refund | + | — |
| transfer | − | + |

For **credit card** accounts the balance is the amount owed ("Outstanding"), so every effect
is negated: purchases increase it, and payments and refunds decrease it.

**Example (bank).** Opening 50,000.00, then income 80,000.00 and expenses 12,000.00, gives
**118,000.00**.

**Tests:** `tests/unit/test_balances.py::test_bank_balance_scenario` and
`tests/integration/test_transactions.py::test_balance_after_income_and_expenses`.

**Example (card).** Purchases of 15,000.00 and then a 10,000.00 bill payment from the bank
leave the card outstanding at **5,000.00**, and the bank is 10,000.00 lower.

**Tests:** `tests/unit/test_balances.py::test_card_purchase_and_bill_payment` and
`tests/integration/test_transactions.py::test_card_bill_payment_is_transfer`.

## F10. Liquid funds

**Definition.** `Liquid funds = Σ balances of non-archived bank and cash accounts`. Wallet
balances are reported separately (`wallet_balance`), and credit card outstanding is reported
separately as a liability. On the dashboard, the current value is taken as of
min(period end, today), and the comparison value as of the previous period's end.

**Example.** Bank 118,000.00, cash 2,000.00 and card outstanding 5,000.00 give liquid funds of
**120,000.00** and card outstanding of **5,000.00**.

**Test:** `tests/integration/test_transactions.py::test_accounts_summary_scenario`.

## F11. Expenses by payment method

**Definition.** The net expense per method: `upi`, `cash`, `debit_card`, `credit_card`,
`bank_transfer` and `other`. A refund counts against its own payment method. If it has none,
it counts against the original expense's method, and otherwise against `other`. Because of
this, the methods always **sum to total expenses**.

**Example.** October expenses of 100 (UPI), 200 (cash), 300 (debit card), 400 (credit card)
and 500 (bank transfer), plus a 150 refund of the card purchase. Credit card is **250.00**,
and the methods sum to the total of **1,350.00**.

**Test:** `tests/integration/test_dashboard.py::test_expense_report_by_method_sums_to_total`.

## F12. Reducing-balance EMI & Amortization

**Definition.** EMI is computed using the standard reducing-balance formula:
$$\text{EMI} = P \times r \times \frac{(1+r)^n}{(1+r)^n - 1}$$
where $P$ is principal, $r = \text{annual rate} \div 12 \div 100$, and $n$ is tenure in months, rounded half-up to 2 dp.
When annual rate is 0%, $\text{EMI} = P \div n$, rounded half-up to 2 dp.

Per installment:
- $\text{Interest} = \text{round}(\text{outstanding} \times r)$
- $\text{Principal} = \text{payment} - \text{interest}$
- $\text{Closing} = \text{outstanding} - \text{principal}$

The final installment absorbs any residual rounding so that closing outstanding is exactly **0.00**, and the sum of principal payments equals the original loan principal $P$.

**Example (Standard EMI).** $P = 1,000,000.00$, annual rate $12\%$, $n = 12$ months.
- Monthly EMI: **88,848.79**
- Installment 1: interest 10,000.00, principal 78,848.79, closing 921,151.21
- Installment 12 (final): payment 88,848.76, principal 87,969.07, interest 879.69, closing 0.00
- Total interest payable: **66,185.45**
- Total principal: **1,000,000.00**

**Tests:** `tests/unit/test_calculations_p1.py::test_emi_spec_examples`,
`tests/unit/test_calculations_p1.py::test_amortization_schedule_spec_example`.

**Example (Zero-interest).** $P = 100,000.00$, annual rate $0\%$, $n = 12$ months.
- Installments 1–11: **8,333.33**
- Installment 12: **8,333.37** (absorbs 0.04 remainder), closing 0.00.

**Test:** `tests/unit/test_calculations_p1.py::test_zero_rate_amortization_schedule`.

**Example (Home loan).** $P = 5,000,000.00$, annual rate $8.5\%$, $n = 240$ months.
- Computed EMI: **43,391.16**

**Test:** `tests/unit/test_calculations_p1.py::test_emi_spec_examples`.

## F13. Loan Prepayments, Rate Changes and Simulations

**Definition.**
- **Prepayment**: reduces loan outstanding principal; user chooses between "reduce tenure" (keeps EMI amount constant, ending date earlier) and "reduce EMI" (recalculates lower EMI for remaining tenure).
- **Rate change**: updates annual interest rate from effective date; user chooses between "keep tenure" (EMI adjusts) and "keep EMI" (tenure extends). Rejects negative amortization if EMI $\le$ monthly interest.
- **Simulation**: evaluates one-time prepayment, recurring extra monthly payment, or rate change without saving to the database.

**Tests:** `tests/unit/test_calculations_p1.py::test_prepayment_reduce_tenure`,
`tests/unit/test_calculations_p1.py::test_rate_change_scenarios`,
`tests/unit/test_calculations_p1.py::test_loan_simulation`.

## F14. Monthly Budgets & Utilization

**Definition.**
$$\text{Utilization} = \frac{\text{Actual Expenses}}{\text{Budget}} \times 100$$
rounded half-up to 2 dp. $\text{Remaining} = \text{Budget} - \text{Actual Expenses}$. A budget of zero is not permitted.

**Example.** Budget 60,000.00 and actual expenses 45,000.00 give utilization of **75.00** and remaining **15,000.00**.

**Example (Overspent).** Budget 12,000.00 and actual expenses 13,500.00 give utilization of **112.50** and remaining **-1,500.00**.

**Test:** `tests/unit/test_calculations_p1.py::test_budget_utilization_and_remaining`.

## F15. Savings Target & Goal Projections

**Definition.**
- **Savings Target Achievement**: $\text{Actual Savings} \div \text{Target} \times 100$. If actual savings is negative, achievement is **0.00** and shortfall is $\text{Target} - \text{Actual}$.
- **Goal Progress**: $\min(100.00, \text{round}(\text{Current Amount} \div \text{Target Amount} \times 100))$.
- **Required Monthly Contribution**: $\text{Remaining} \div \text{Months Left}$. Returns `null` if the target date has passed (overdue).
- **Estimated Completion Date**: $\lceil \text{Remaining} \div \text{Average 3-month net contribution} \rceil$ months ahead. Returns `null` ("Cannot estimate") if the 3-month average is $\le 0$.

**Example (Savings Target).** Target 30,000.00 and actual savings 36,000.00 give achievement **120.00**. With actual savings -5,000.00, achievement is **0.00** and shortfall is **35,000.00**.

**Example (Goal Contribution).** Remaining 225,000.00 and 9 full months left before target date give required monthly contribution of **25,000.00**.

**Tests:** `tests/unit/test_calculations_p1.py::test_savings_target_achievement`,
`tests/unit/test_calculations_p1.py::test_goal_projections`.

## F16. Emergency Fund Coverage

**Definition.**
$$\text{Emergency Fund Coverage (months)} = \frac{\text{Liquid Savings}}{\text{Essential Monthly Expenses}}$$
where:
- $\text{Liquid Savings} = \text{bank} + \text{cash} + \text{wallet balances} + \text{liquid manual assets}$.
- $\text{Essential Monthly Expenses} = \text{average of last 3 complete months of essential expenses (excluding Loan Interest)} + \text{current monthly EMI commitment}$.
When essential expenses are zero, coverage is **null** (displayed as "N/A").

**Example.** Liquid savings of 300,000.00 and essential monthly expenses of 50,000.00 give coverage of **6.00** months.

**Test:** `tests/unit/test_calculations_p1.py::test_emergency_fund_coverage`.

## F17. Net Worth & Growth

**Definition.**
$$\text{Net Worth} = \text{Total Assets} - \text{Total Liabilities}$$
as of a date.
- Assets: bank, cash, wallet balances ($\ge 0$), manual asset valuations $\le$ as_of (excluding closed), and investment holdings.
- Liabilities: credit card outstanding, loan outstanding principal $\le$ as_of, other liabilities $\le$ as_of (excluding closed), and negative bank balances (overdraft).
- MoM / YoY growth:
$$\text{Growth \%} = \frac{\text{Current} - \text{Base}}{|\text{Base}|} \times 100$$
When Base is missing, growth is **null** ("—"). When Base is zero, percentage is **null**.

**Example.** Bank 300,000.00, FD 205,000.00, Gold 165,000.00, Card outstanding 25,000.00, Home loan outstanding 4,800,000.00:
- Total assets: **670,000.00**
- Total liabilities: **4,825,000.00**
- Net worth: **-4,155,000.00**

**Example (Overdraft).** Bank balance -2,000.00 is counted in liabilities as **2,000.00**, giving total liabilities 2,000.00 and net worth **-2,000.00**.

**Tests:** `tests/unit/test_calculations_p1.py::test_compute_net_worth_spec_example`,
`tests/unit/test_calculations_p1.py::test_compute_net_worth_overdraft`,
`tests/unit/test_calculations_p1.py::test_growth_computation`.

## Consistency guarantee

The dashboard tiles, the dashboard and report trends, the category breakdown, the expense,
income and savings reports, and the transaction list totals all return identical figures for
the same period.

**Test:** `tests/integration/test_dashboard.py::test_dashboard_and_reports_identical`.
