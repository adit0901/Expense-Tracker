import { type Page, expect } from '@playwright/test'

export const PASSWORD = 'Correct-Horse-Battery-9'

export function uniqueEmail(prefix = 'e2e'): string {
  return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 1e6)}@example.com`
}

export async function register(page: Page, email = uniqueEmail(), name = 'Asha Rao'): Promise<string> {
  await page.goto('/register')
  await page.getByLabel('Full name').fill(name)
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password', { exact: true }).fill(PASSWORD)
  await page.getByLabel('Confirm password').fill(PASSWORD)
  await page.getByRole('button', { name: 'Create account' }).click()
  await expect(page.getByRole('heading', { name: 'Overview' })).toBeVisible()
  return email
}

export async function addAccount(page: Page, name: string, opening = '0.00', type = 'Bank account', openingDate?: string): Promise<void> {
  await page.goto('/settings/accounts')
  await page.getByRole('button', { name: 'Add account' }).first().click()
  const dialog = page.getByRole('dialog')
  await dialog.getByLabel('Name').fill(name)
  if (type !== 'Bank account') {
    await dialog.getByLabel('Type').click()
    await page.getByRole('option', { name: type }).click()
  }
  await dialog.getByLabel(/Opening (balance|outstanding)/).fill(opening)
  if (openingDate) {
    await dialog.getByLabel('Opening date').fill(openingDate)
  }
  await dialog.getByRole('button', { name: 'Add account' }).click()
  await expect(dialog).toBeHidden()
  await expect(page.getByText(name, { exact: true })).toBeVisible()
}

export interface TxnInput {
  type?: 'Expense' | 'Income' | 'Transfer' | 'Refund'
  account: string
  category?: string
  amount: string
  method?: string
  description?: string
  date?: string
  breakdown?: { gross: string; deductions: [string, string][] }
}

export async function addTransaction(page: Page, t: TxnInput): Promise<void> {
  await page.goto('/transactions')
  await page.getByRole('button', { name: 'Add transaction' }).first().click()
  const dialog = page.getByRole('dialog')
  if (t.type && t.type !== 'Expense') await dialog.getByLabel(t.type, { exact: true }).check()
  await dialog.getByLabel('Account', { exact: true }).selectOption({ label: t.account })
  if (t.category) await dialog.getByLabel('Category').selectOption({ label: t.category })
  await dialog.getByLabel('Amount (₹)').fill(t.amount)
  if (t.date) await dialog.getByLabel('Date', { exact: true }).fill(t.date)
  if (t.method) await dialog.getByLabel('Payment method').selectOption({ label: t.method })
  if (t.description) await dialog.getByLabel('Description (optional)').fill(t.description)
  if (t.breakdown) {
    await dialog.getByLabel('Record gross salary and deductions').check()
    await dialog.getByLabel('Gross salary (₹)').fill(t.breakdown.gross)
    for (const [i, [name, amount]] of t.breakdown.deductions.entries()) {
      await dialog.getByRole('button', { name: 'Add deduction' }).click()
      await dialog.getByLabel(`Deduction ${i + 1} name`).fill(name)
      await dialog.getByLabel('Amount', { exact: true }).nth(i).fill(amount)
    }
  }
  await dialog.getByRole('button', { name: 'Save transaction' }).click()
  await expect(dialog).toBeHidden()
}
