# Spec Delta

## ADDED Requirements

### Requirement: Loan payment transaction type
The system SHALL support a `loan_payment` transaction type, created through the loans capability, that debits a source account and carries a principal component and an interest component summing to the amount. The principal component SHALL reduce the linked loan's outstanding principal; only the interest component SHALL count as an expense in the system category "Loan Interest".

#### Scenario: Loan payment in expenses
- **WHEN** a confirmed EMI of 43391.16 has interest 35416.67 and principal 7974.49
- **THEN** monthly expenses include 35416.67 under Loan Interest and exclude 7974.49

#### Scenario: Direct creation blocked
- **WHEN** a client creates a `loan_payment` through the generic transaction endpoint without a loan reference
- **THEN** the system responds 422

### Requirement: Prepayment recorded as loan payment without interest
A loan prepayment SHALL be recorded as a `loan_payment` transaction whose interest component is 0.00 (unless the lender charges a fee, recorded as a separate expense).

#### Scenario: Prepayment not an expense
- **WHEN** a user records a 500000.00 prepayment
- **THEN** monthly expenses are unchanged and the bank balance decreases by 500000.00
