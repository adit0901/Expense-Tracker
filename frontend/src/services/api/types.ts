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
