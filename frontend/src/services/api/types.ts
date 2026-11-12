import type { components } from '@/types/api'

type S = components['schemas']

export type UserOut = S['UserOut']
export type PreferencesOut = S['PreferencesOut']
export type PreferencesUpdate = S['PreferencesUpdate']
export type TokenOut = S['TokenOut']
export type AccountOut = S['AccountOut']
export type AccountCreate = S['AccountCreate']
export type AccountUpdate = S['AccountUpdate']
export type AccountsSummary = S['AccountsSummary']
export type AccountType = AccountOut['type']
export type CategoryOut = S['CategoryOut']
export type CategoryCreate = S['CategoryCreate']
export type CategoryUpdate = S['CategoryUpdate']
export type CategoryKind = CategoryOut['kind']
export type TransactionOut = S['TransactionOut']
export type TransactionCreate = S['TransactionCreate']
export type TransactionUpdate = S['TransactionUpdate']
export type TransactionType = TransactionOut['type']
export type PaymentMethod = NonNullable<TransactionOut['payment_method']>
export type TransactionTotals = S['TransactionTotals']
export type DuplicateCheckOut = S['DuplicateCheckOut']
export type AttachmentOut = S['AttachmentOut']
export type ImportBatchOut = S['ImportBatchOut']
export type ImportRowOut = S['ImportRowOut']
export type IncomeSourceOut = S['IncomeSourceOut']
export type IncomeSourceCreate = S['IncomeSourceCreate']
export type IncomeReport = S['IncomeReport']
export type ExpenseReport = S['ExpenseReport']
export type SavingsTrend = S['SavingsTrend']
export type MonthFigures = S['MonthFigures']
export type Overview = S['Overview']
export type Tile = S['Tile']
export type CategoryBreakdown = S['CategoryBreakdown']

// P1 Budgets
export type BudgetResponse = S['BudgetResponse']
export type BudgetLineResponse = S['BudgetLineResponse']
export type BudgetLineInput = S['BudgetLineInput']
export type SetBudgetRequest = S['SetBudgetRequest']
export type BudgetComparisonResponse = S['BudgetComparisonResponse']
export type BudgetMonthComparisonItem = S['BudgetMonthComparisonItem']
export type BudgetAlertResponse = S['BudgetAlertResponse']

// P1 Savings & Goals
export type SavingsTargetIn = S['SavingsTargetIn']
export type SavingsTargetOut = S['SavingsTargetOut']
export type SavingsTargetDashboardTile = S['SavingsTargetDashboardTile']
export type GoalOut = S['GoalOut']
export type GoalType = GoalOut['type']
export type GoalCreate = S['GoalCreate']
export type GoalUpdate = S['GoalUpdate']
export type GoalContributionOut = S['GoalContributionOut']
export type GoalContributionCreate = S['GoalContributionCreate']

// P1 Assets & Liabilities
export type AssetOut = S['AssetOut']
export type AssetCreate = S['AssetCreate']
export type AssetUpdate = S['AssetUpdate']
export type AssetCloseIn = S['AssetCloseIn']
export type AssetValuationOut = S['AssetValuationOut']
export type AssetValuationIn = S['AssetValuationIn']
export type LiabilityOut = S['LiabilityOut']
export type LiabilityCreate = S['LiabilityCreate']
export type LiabilityUpdate = S['LiabilityUpdate']
export type LiabilityCloseIn = S['LiabilityCloseIn']
export type LiabilityBalanceOut = S['LiabilityBalanceOut']
export type LiabilityBalanceIn = S['LiabilityBalanceIn']

// P1 Loans & EMIs
export type LoanOut = S['LoanOut']
export type LoanType = LoanOut['type']
export type LoanCreate = S['LoanCreate']
export type LoanUpdate = S['LoanUpdate']
export type LoanScheduleOut = S['LoanScheduleOut']
export type InstallmentOut = S['InstallmentOut']
export type LoanPaymentCreate = S['LoanPaymentCreate']
export type LoanPaymentOut = S['LoanPaymentOut']
export type LoanEventCreate = S['LoanEventCreate']
export type LoanEventOut = S['LoanEventOut']
export type LoanSimulateRequest = S['LoanSimulateRequest']
export type LoanSimulateOut = S['LoanSimulateOut']
export type LoanSummaryOut = S['LoanSummaryOut']
export type LoanTrendPoint = S['LoanTrendPoint']

// P1 Net Worth
export type NetWorthOut = S['NetWorthOut']
export type NetWorthSnapshotOut = S['NetWorthSnapshotOut']
export type NetWorthSnapshotCreate = S['NetWorthSnapshotCreate']
export type NetWorthPoint = S['NetWorthPoint']
export type EmergencyFundMetricsOut = S['EmergencyFundMetricsOut']
export type PlanningTile = S['PlanningTile']
export type BudgetAlertDashboardItem = S['BudgetAlertDashboardItem']

export interface PageMeta {
  page: number
  page_size: number
  total_items: number
  total_pages: number
}

export interface Envelope<T> {
  data: T
  meta: Record<string, unknown>
}

export interface Page<T, M extends PageMeta = PageMeta> {
  data: T[]
  meta: M
}

export interface ErrorDetail {
  field?: string
  message?: string
  [key: string]: unknown
}
