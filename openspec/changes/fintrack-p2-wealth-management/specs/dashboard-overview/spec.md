# Spec Delta

## ADDED Requirements

### Requirement: Investment tiles and chart
The Overview page SHALL additionally show Total Investment Value (INR), unrealized return % and the investment portfolio allocation (India vs US, top holdings), linking to Portfolio Overview, with the oldest price timestamp used.

#### Scenario: Investment tile
- **WHEN** a user with holdings opens Overview
- **THEN** the Total Investment Value tile shows the INR value and "Prices as of" the oldest price timestamp used

#### Scenario: Unpriced notice
- **WHEN** some holdings have no price
- **THEN** the tile notes how many holdings are excluded
