import { expect, test } from '@playwright/test'

import { addAccount, register } from './helpers'

test('create loan → confirm EMI → dashboard expenses include only interest and net worth reflects reduced liability', async ({ page }) => {
  // 1. Register new user and set up funded bank account
  await register(page)
  await expect(page.getByRole('main').getByText('Welcome to FinTrack')).toBeVisible()
  await addAccount(page, 'HDFC Bank', '1000000.00', 'Bank account', '2026-10-01')

  // 2. Navigate to Loans & EMIs and create a new Home Loan
  await page.goto('/loans')
  await expect(page.getByRole('heading', { name: 'Loans & EMIs' })).toBeVisible()

  await page.getByRole('button', { name: 'Add loan' }).first().click()
  const loanDialog = page.getByRole('dialog')
  await expect(loanDialog).toBeVisible()

  await loanDialog.getByLabel('Loan Type').selectOption('home')
  await loanDialog.getByLabel('Lender / Bank').fill('SBI Home Loan')
  await loanDialog.getByLabel('Principal (₹)').fill('1000000.00')
  await loanDialog.getByLabel('Interest Rate (% p.a.)').fill('12.00')
  await loanDialog.getByLabel('Tenure (Months)').fill('12')
  await loanDialog.getByLabel('Disbursal / Start Date').fill('2026-10-10')
  await loanDialog.getByLabel('First EMI Date (Optional)').fill('2026-11-10')
  await loanDialog.getByRole('button', { name: 'Create Loan' }).click()
  await expect(loanDialog).toBeHidden()

  // Verify loan appears on page
  await expect(page.getByText('SBI Home Loan')).toBeVisible()
  await expect(page.getByText('₹88,848.79').first()).toBeVisible()

  // 3. Open schedule and pay first installment
  await page.getByRole('button', { name: 'Schedule' }).first().click()
  const scheduleDialog = page.getByRole('dialog')
  await expect(scheduleDialog).toBeVisible()
  await expect(scheduleDialog.getByText('Amortization Schedule: SBI Home Loan')).toBeVisible()

  // Click Pay on the first installment
  await scheduleDialog.getByRole('button', { name: 'Pay' }).first().click()

  // 4. Confirm Payment dialog
  const payDialog = page.getByRole('dialog').filter({ hasText: 'Confirm EMI Payment' })
  await expect(payDialog).toBeVisible()
  // Check the principal vs interest split display
  await expect(payDialog.getByText('₹78,848.79')).toBeVisible()
  await expect(payDialog.getByText('₹10,000.00')).toBeVisible()

  // Select HDFC Bank as source account
  await payDialog.getByLabel('Source account').selectOption({ label: 'HDFC Bank (bank)' })
  await payDialog.getByRole('button', { name: 'Confirm EMI Payment' }).click()
  await expect(payDialog).toBeHidden()

  // Close schedule dialog
  await page.keyboard.press('Escape')

  // 5. Navigate to Dashboard Overview
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Overview' })).toBeVisible()

  // Verify Key Figures: Total expenses contains ONLY the interest component (₹10,000.00)
  const keyFigures = page.getByRole('region', { name: 'Key figures' })
  await expect(keyFigures.getByText('Total expenses').locator('..')).toContainText('₹10,000.00')

  // Verify Planning & Balance Sheet: Net Worth reflects reduced liability
  // Assets = 1,000,000 - 88,848.79 = 911,151.21
  // Liabilities = 921,151.21
  // Net Worth = -10,000.00
  const balanceSheet = page.getByRole('region', { name: 'Planning and balance sheet' })
  await expect(balanceSheet.getByRole('link', { name: /Outstanding Loans/ })).toContainText('₹9,21,151.21')
  await expect(balanceSheet.getByRole('link', { name: /Total Liabilities/ })).toContainText('₹9,21,151.21')
  await expect(balanceSheet.getByRole('link', { name: /Net Worth/ })).toContainText('-₹10,000.00')

  // 6. Navigate to Net Worth page and verify detailed balance sheet
  await page.goto('/net-worth')
  await expect(page.getByRole('heading', { name: 'Net Worth' })).toBeVisible()
  await expect(page.getByText('-₹10,000.00')).toBeVisible()
  await expect(page.getByText('₹9,21,151.21')).toBeVisible()
})
