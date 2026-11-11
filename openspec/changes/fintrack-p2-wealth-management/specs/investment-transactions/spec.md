# Spec Delta

## Purpose

Records the complete history of a user's investment activity (buys, sells, dividends, splits, bonus issues and charges) and defines the cost-basis rules from which holdings and realized profit/loss are derived.

## ADDED Requirements

### Requirement: Buy transactions
A user SHALL record a buy with: account, security, trade date, quantity (> 0, up to 8 decimals for US fractional shares; whole numbers for IN), price per unit (> 0), charges (≥ 0, itemizable: brokerage, STT, exchange fees, stamp duty, GST, other) and, for USD trades, the USD-INR rate. Total cost = quantity × price + charges.

#### Scenario: Buy with charges
- **WHEN** a user buys 10 TCS at 3500.00 with charges 20.00
- **THEN** the holding has 10 units, total cost 35020.00 and average cost 3502.00

#### Scenario: Fractional IN quantity
- **WHEN** a user enters 2.5 shares for an NSE stock
- **THEN** the system responds 422

### Requirement: Weighted-average cost basis
Average cost per unit SHALL equal total cost ÷ quantity held, where buys add their total cost, and sells remove average cost × quantity sold. Sells SHALL NOT change the average cost of remaining units.

#### Scenario: Average after sell and buy
- **WHEN** after holding 6 units at average 3502.00 the user buys 4 more at 3600.00 with no charges
- **THEN** the holding is 10 units with total cost 35412.00 and average cost 3541.20

### Requirement: Sell transactions and realized profit/loss
A user SHALL record full or partial sells with quantity, price and charges. Quantity sold SHALL NOT exceed quantity held on the trade date. Realized P/L = (quantity × price − charges) − average cost × quantity.

#### Scenario: Partial sale
- **WHEN** a user holding 10 TCS at average 3502.00 sells 4 at 3800.00 with charges 15.00
- **THEN** realized P/L is 1177.00 and 6 units remain at average 3502.00

#### Scenario: Overselling
- **WHEN** a user tries to sell 12 units while holding 10
- **THEN** the system responds 422 `insufficient_quantity`

### Requirement: Dividends
A user SHALL record cash dividends with security, payment date, gross amount, tax withheld (≥ 0) and net amount (= gross − tax withheld) in the security currency. Dividends SHALL NOT change quantity or cost basis.

#### Scenario: US dividend with withholding
- **WHEN** a user records a 10.00 USD gross dividend with 2.50 USD withheld
- **THEN** net dividend is 7.50 USD and the holding's cost basis is unchanged

### Requirement: Stock splits and bonus issues
A user SHALL record a split (ratio new:old, e.g. 5:1) or bonus issue (ratio bonus:held, e.g. 1:1) effective on an ex-date. Quantity SHALL be adjusted by the ratio and total cost SHALL stay unchanged, so average cost scales inversely. Fractional entitlements in IN SHALL be rounded down.

#### Scenario: Split
- **WHEN** a holding of 6 units at average 3502.00 undergoes a 5:1 split
- **THEN** it becomes 30 units at average 700.40 with total cost 21012.00

#### Scenario: Bonus
- **WHEN** 30 units at average 700.40 receive a 1:1 bonus
- **THEN** it becomes 60 units at average 350.20

### Requirement: Edit and delete with recomputation
Editing or deleting any investment transaction SHALL recompute holdings and realized P/L for that holding from its full history in date order; changes that would make quantity negative at any point SHALL be rejected.

#### Scenario: Deleting a buy that later sells depend on
- **WHEN** a user deletes a buy such that an existing later sell exceeds the quantity held
- **THEN** the system responds 409 and nothing changes

### Requirement: Investment history
A user SHALL be able to list investment transactions filtered by account, security, type and date range, and export them as CSV.

#### Scenario: Security history
- **WHEN** a user views the history of TCS
- **THEN** all buys, sells, dividends, splits and bonuses for TCS are listed in date order with running quantity
