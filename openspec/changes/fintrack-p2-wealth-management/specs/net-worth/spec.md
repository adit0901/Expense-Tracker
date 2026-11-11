# Spec Delta

## ADDED Requirements

### Requirement: Investments included in net worth
Total assets SHALL include the INR value of investment holdings as of the reporting date: priced holdings at their latest price on or before that date converted at the applicable USD-INR rate, and unpriced holdings at their INR cost basis labeled "valued at cost".

#### Scenario: Net worth with investments
- **WHEN** a user's other assets are 670000.00 and priced holdings are worth 1000000.00 INR
- **THEN** total assets are 1670000.00 and the breakdown lists Indian stocks and US stocks separately

#### Scenario: Unpriced holding
- **WHEN** a holding has no price and INR cost 50000.00
- **THEN** 50000.00 is included in assets and labeled "valued at cost"

### Requirement: No double counting with manual assets
Stocks and ETFs held in investment accounts SHALL NOT also be entered as manual assets; manual asset types SHALL NOT include stocks or ETFs.

#### Scenario: Stock as manual asset
- **WHEN** a user tries to add a manual asset of type `stocks`
- **THEN** the system responds 422 and points to the Investments section
