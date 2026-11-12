import type {
  AccountOut,
  CategoryOut,
  Overview,
  PreferencesOut,
  TransactionOut,
  UserOut,
} from '@/services/api/types'

export const USER: UserOut = {
  id: '00000000-0000-0000-0000-000000000001',
  email: 'asha@example.com',
  full_name: 'Asha Rao',
  created_at: '2026-01-01T00:00:00Z',
}

export const PREFS: PreferencesOut = {
  currency: 'INR',
  theme: 'system',
  locale: 'en-IN',
  date_format: 'DD/MM/YYYY',
  number_grouping: 'indian',
  week_start: 'monday',
  timezone: 'Asia/Kolkata',
}

export const ACCOUNT: AccountOut = {
  id: 'acc-1',
  name: 'HDFC Savings',
  type: 'bank',
  institution: 'HDFC',
  last4: '1234',
  currency: 'INR',
  opening_balance: '50000.00',
  opening_date: '2026-01-01',
  archived_at: null,
  current_balance: '118000.00',
  is_liability: false,
  balance_label: 'Balance',
  created_at: '2026-01-01T00:00:00Z',
}

export const CARD: AccountOut = {
  ...ACCOUNT,
  id: 'acc-2',
  name: 'HDFC Card',
  type: 'credit_card',
  last4: '9876',
  opening_balance: '0.00',
  current_balance: '5000.00',
  is_liability: true,
  balance_label: 'Outstanding',
}

function cat(id: string, name: string, kind: 'income' | 'expense', extra: Partial<CategoryOut> = {}): CategoryOut {
  return { id, name, kind, parent_id: null, color: '#1d4ed8', icon: null, is_essential: false, is_system: false, ...extra }
}

export const CATEGORIES: CategoryOut[] = [
  cat('cat-food', 'Food', 'expense', { is_essential: true }),
  cat('cat-groceries', 'Groceries', 'expense', { parent_id: 'cat-food' }),
  cat('cat-ent', 'Entertainment', 'expense'),
  cat('cat-others', 'Others', 'expense'),
  cat('cat-loan', 'Loan Interest', 'expense', { is_system: true, is_essential: true }),
  cat('cat-salary', 'Salary', 'income'),
]

export function txn(overrides: Partial<TransactionOut> = {}): TransactionOut {
  return {
    id: 'txn-1',
    type: 'expense',
    status: 'posted',
    account_id: ACCOUNT.id,
    account_name: ACCOUNT.name,
    counter_account_id: null,
    counter_account_name: null,
    category_id: 'cat-food',
    category_name: 'Food',
    parent_category_id: null,
    parent_category_name: null,
    income_source_id: null,
    amount: '450.00',
    currency: 'INR',
    txn_date: '2026-11-10',
    payment_method: 'upi',
    payee: 'Swiggy',
    description: 'Dinner',
    notes: null,
    tags: [],
    refund_of_id: null,
    import_batch_id: null,
    salary_breakdown: null,
    attachments: [],
    created_at: '2026-11-10T10:00:00Z',
    updated_at: '2026-11-10T10:00:00Z',
    ...overrides,
  }
}

const tile = (value: string | null, previous: string | null, change: string | null, kind = 'percent') =>
  ({ value, previous, change, change_kind: kind })

export function overview(overrides: Partial<Overview> = {}): Overview {
  return {
    period: { start: '2026-11-01', end: '2026-11-30', label: 'Nov 2026', granularity: 'month' },
    previous_period: { start: '2026-10-01', end: '2026-10-31', label: 'Oct 2026', granularity: 'month' },
    income: tile('120000.00', '100000.00', '20.00'),
    expenses: tile('90000.00', '60000.00', '50.00'),
    savings: tile('30000.00', '40000.00', '-25.00'),
    savings_rate: tile('25.00', '40.00', '-15.00', 'points'),
    liquid_funds: tile('120000.00', '0.00', null),
    has_transactions: true,
    has_accounts: true,
    net_worth: { value: '2500000.00', previous: null, change: null, change_kind: 'percent' },
    total_assets: { value: '3500000.00', previous: null, change: null, change_kind: 'percent' },
    total_liabilities: { value: '1000000.00', previous: null, change: null, change_kind: 'percent' },
    outstanding_loans: { value: '921151.21', previous: null, change: null, change_kind: 'percent' },
    monthly_emi_commitment: { value: '88848.79', previous: null, change: null, change_kind: 'percent' },
    savings_target: {
      configured: true,
      target_amount: '30000.00',
      actual_savings: '36000.00',
      achievement_pct: '120.00',
      shortfall: '0.00',
    },
    budget_utilization_pct: '75.00',
    budget_alerts: [
      {
        category_id: 'cat-food',
        category_name: 'Food',
        budgeted: '12000.00',
        spent: '13500.00',
        utilization_pct: '112.50',
        threshold_crossed: 100,
      },
    ],
    net_worth_trend: [
      { as_of: '2026-10-31', net_worth: '2400000.00', total_assets: '3400000.00', total_liabilities: '1000000.00' },
      { as_of: '2026-11-30', net_worth: '2500000.00', total_assets: '3500000.00', total_liabilities: '1000000.00' },
    ],
    asset_allocation: [
      { category: 'Bank & Cash', amount: '120000.00', share_pct: '3.43' },
      { category: 'Real Estate', amount: '3380000.00', share_pct: '96.57' },
    ],
    loan_trend: [
      { month: '2026-10', total_outstanding: '950000.00' },
      { month: '2026-11', total_outstanding: '921151.21' },
    ],
    ...overrides,
  }
}
