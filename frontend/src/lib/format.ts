/**
 * Formatting only. Amounts arrive from the API as decimal strings and are never used for
 * arithmetic in the browser (spec: financial-calculations).
 */
export type NumberGrouping = 'indian' | 'international'
export type DateFormat = 'DD/MM/YYYY' | 'MM/DD/YYYY' | 'YYYY-MM-DD'

const moneyFormatters = new Map<string, Intl.NumberFormat>()

function moneyFormatter(grouping: NumberGrouping, currency: string): Intl.NumberFormat {
  const key = `${grouping}:${currency}`
  let f = moneyFormatters.get(key)
  if (!f) {
    f = new Intl.NumberFormat(grouping === 'indian' ? 'en-IN' : 'en-US', {
      style: 'currency',
      currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })
    moneyFormatters.set(key, f)
  }
  return f
}

/** "1234567.89" -> "₹12,34,567.89" (Indian) or "₹1,234,567.89" (international). */
export function formatMoney(
  amount: string | null | undefined,
  opts: { grouping?: NumberGrouping; currency?: string } = {},
): string {
  if (amount === null || amount === undefined || amount === '') return '—'
  const f = moneyFormatter(opts.grouping ?? 'indian', opts.currency ?? 'INR')
  // Intl accepts decimal strings exactly (no float rounding) in modern engines.
  return f.format(amount as unknown as number)
}

/** Percentages arrive as strings with 2 dp; null means not applicable. */
export function formatPercent(value: string | null | undefined, opts: { signed?: boolean } = {}): string {
  if (value === null || value === undefined) return 'N/A'
  const sign = opts.signed && !value.startsWith('-') && value !== '0.00' ? '+' : ''
  return `${sign}${value}%`
}

export function formatChange(value: string | null | undefined, kind: string): string {
  if (value === null || value === undefined) return '—'
  const sign = value.startsWith('-') ? '' : value === '0.00' ? '' : '+'
  return kind === 'points' ? `${sign}${value} pts` : `${sign}${value}%`
}

/** ISO date "2026-10-05" -> preferred display format. */
export function formatDate(iso: string | null | undefined, format: DateFormat = 'DD/MM/YYYY'): string {
  if (!iso) return '—'
  const [y, m, d] = iso.slice(0, 10).split('-')
  if (!y || !m || !d) return iso
  switch (format) {
    case 'MM/DD/YYYY':
      return `${m}/${d}/${y}`
    case 'YYYY-MM-DD':
      return `${y}-${m}-${d}`
    default:
      return `${d}/${m}/${y}`
  }
}

export function isNegative(amount: string | null | undefined): boolean {
  return !!amount && amount.trim().startsWith('-')
}

export const PAYMENT_METHOD_LABELS: Record<string, string> = {
  upi: 'UPI',
  cash: 'Cash',
  debit_card: 'Debit card',
  credit_card: 'Credit card',
  bank_transfer: 'Bank transfer',
  other: 'Other',
}

export const TRANSACTION_TYPE_LABELS: Record<string, string> = {
  income: 'Income',
  expense: 'Expense',
  transfer: 'Transfer',
  refund: 'Refund',
}

export const ACCOUNT_TYPE_LABELS: Record<string, string> = {
  bank: 'Bank account',
  cash: 'Cash',
  credit_card: 'Credit card',
  wallet: 'Wallet',
}

/** Today's date as YYYY-MM-DD in the given IANA time zone. */
export function todayIso(timeZone = 'Asia/Kolkata'): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone, year: 'numeric', month: '2-digit', day: '2-digit' })
    .format(new Date())
}
