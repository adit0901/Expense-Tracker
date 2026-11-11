import { expect, test } from '@playwright/test'

import { addAccount, addTransaction, register } from './helpers'

test('register → account → salary with breakdown and expenses → dashboard figures', async ({ page }) => {
  await register(page)
  await expect(page.getByRole('main').getByText('Welcome to FinTrack')).toBeVisible()
  await addAccount(page, 'HDFC Savings', '10000.00')

  await addTransaction(page, {
    type: 'Income', account: 'HDFC Savings', category: 'Salary', amount: '123000.00', description: 'November salary',
    breakdown: { gross: '150000.00', deductions: [['Income Tax/TDS', '25000.00'], ['EPF employee contribution', '1800.00'], ['Professional Tax', '200.00']] },
  })
  await addTransaction(page, { account: 'HDFC Savings', category: 'Food', amount: '450.00', method: 'UPI', description: 'Dinner' })
  await addTransaction(page, { account: 'HDFC Savings', category: 'Rent', amount: '20000.00', method: 'Bank transfer', description: 'Rent' })

  await page.goto('/')
  const tiles = page.getByRole('region', { name: 'Key figures' })
  await expect(tiles.getByText('Total income').locator('..')).toContainText('₹1,23,000.00')
  await expect(tiles.getByText('Total expenses').locator('..')).toContainText('₹20,450.00')
  await expect(tiles.getByText('Savings', { exact: true }).locator('..')).toContainText('₹1,02,550.00')
  await expect(tiles.getByText('Savings rate').locator('..')).toContainText('83.37%')
  await expect(tiles.getByText('Liquid funds').locator('..')).toContainText('₹1,12,550.00')
  // TDS is not an expense, and the recent list shows the entries.
  await expect(page.getByRole('list', { name: 'Recent transactions' })).toContainText('Dinner')

  // Drill-down from the category legend.
  await page.getByRole('button', { name: /View transactions for Rent/ }).click()
  await expect(page).toHaveURL(/category_id=/)
  await expect(page.getByRole('cell', { name: 'Rent' }).first()).toBeVisible()
})
