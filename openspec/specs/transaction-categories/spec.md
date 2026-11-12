# transaction-categories Specification

## Purpose

Gives every income and expense a meaningful classification, with sensible defaults and user-defined categories and subcategories, so spending and income can be analyzed and budgeted.

## Requirements

### Requirement: Default categories seeded per user
On registration the system SHALL create default expense categories (Food, Rent, Shopping, Travel, Healthcare, Utilities, Fuel, Entertainment, Insurance, Education, Loan Interest, Others) and default income categories (Salary, Bonus, Freelance, Business, Rental, Dividends, Interest, Other Income).

#### Scenario: New user categories
- **WHEN** a new user lists expense categories
- **THEN** the default expense categories above are returned

### Requirement: Category kinds
Each category SHALL have a kind of `income` or `expense`. A transaction SHALL only use a category whose kind matches the transaction type.

#### Scenario: Mismatched category
- **WHEN** a user records an expense with the category "Salary"
- **THEN** the system responds 422 `category_kind_mismatch`

### Requirement: Custom categories and subcategories
A user SHALL be able to create, rename and recolor categories, and create subcategories one level deep under a category. Names SHALL be unique per user within the same parent and kind, case-insensitively.

#### Scenario: Create subcategory
- **WHEN** a user creates "Groceries" under "Food"
- **THEN** expenses can be assigned to Food › Groceries and roll up into Food totals

#### Scenario: Third level rejected
- **WHEN** a user tries to create a subcategory under "Groceries"
- **THEN** the system responds 422

### Requirement: Essential-expense flag
Expense categories SHALL carry an `is_essential` flag (defaults: Rent, Utilities, Healthcare, Insurance, Education, Food and Loan Interest essential) that users can change, used for emergency-fund calculations.

#### Scenario: Toggle essential
- **WHEN** a user marks "Fuel" as essential
- **THEN** future essential-expense totals include Fuel transactions

### Requirement: Deleting categories preserves transactions
Deleting a category in use SHALL require choosing a replacement category of the same kind; its transactions (and subcategories' transactions) SHALL be reassigned atomically. System-managed categories (Loan Interest) SHALL NOT be deletable.

#### Scenario: Delete with reassignment
- **WHEN** a user deletes "Entertainment" and selects "Others" as replacement
- **THEN** all Entertainment transactions now belong to Others

#### Scenario: Delete in-use category without replacement
- **WHEN** a user deletes an in-use category without a replacement
- **THEN** the system responds 409 `category_in_use`
