import { expect, test } from '@playwright/test'

import { addAccount, addTransaction, register } from './helpers'

test('set budget → add expenses past 80% → alert appears once; create goal → contribute → progress updates', async ({ page }) => {
  // 1. Register new user and set up account
  await register(page)
  await expect(page.getByRole('main').getByText('Welcome to FinTrack')).toBeVisible()
  await addAccount(page, 'HDFC Savings', '100000.00', 'Bank account', '2026-10-01')

  // 2. Set budget: Food = 10,000.00
  await page.goto('/budgets')
  await expect(page.getByRole('heading', { name: 'Budgets' })).toBeVisible()

  await page.getByRole('button', { name: /Set Budget|Edit Budget/i }).click()
  const budgetDialog = page.getByRole('dialog')
  await expect(budgetDialog).toBeVisible()

  await budgetDialog.getByRole('button', { name: 'Add Category' }).click()
  await budgetDialog.getByLabel('Category', { exact: true }).selectOption({ label: 'Food' })
  await budgetDialog.getByLabel('Budget amount').fill('10000.00')
  await budgetDialog.getByRole('button', { name: 'Save Budget' }).click()
  await expect(budgetDialog).toBeHidden()

  // Verify Food budget appears in category budgets table
  await expect(page.getByRole('cell', { name: 'Food' })).toBeVisible()
  await expect(page.getByText('₹10,000.00').first()).toBeVisible()

  // 3. Add expense past 80%: Food expense of 8,500.00 (85% utilization)
  await addTransaction(page, {
    account: 'HDFC Savings',
    category: 'Food',
    amount: '8500.00',
    method: 'UPI',
    description: 'Groceries and snacks',
  })

  // 4. Check alert appears once
  await page.goto('/budgets')
  await expect(page.getByRole('heading', { name: 'Budgets' })).toBeVisible()

  // Active Spending Alerts list should show crossed 80% threshold
  const alertsList = page.getByRole('list', { name: 'Active alerts' })
  await expect(alertsList).toBeVisible()
  await expect(alertsList.getByText(/Food.*crossed 80% threshold/i)).toBeVisible()
  // Alert appears once
  await expect(alertsList.locator('li')).toHaveCount(1)

  // Also check on Dashboard Overview
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Overview' })).toBeVisible()
  await expect(page.getByText('Budget Status & Spending Alerts')).toBeVisible()
  await expect(page.getByText('Spent ₹8,500.00 of ₹10,000.00')).toBeVisible()
  await expect(page.getByText('85.00%')).toBeVisible()

  // 5. Create Goal: Emergency Fund with target 50,000.00
  await page.goto('/goals')
  await expect(page.getByRole('heading', { name: 'Savings & Goals' })).toBeVisible()

  await page.getByRole('button', { name: 'New Goal' }).click()
  const goalDialog = page.getByRole('dialog')
  await expect(goalDialog).toBeVisible()

  await goalDialog.getByLabel('Goal Name').fill('Emergency Fund')
  await goalDialog.getByLabel('Category / Type').selectOption({ label: 'Emergency Fund' })
  await goalDialog.getByLabel('Target Amount (₹)').fill('50000.00')
  await goalDialog.getByRole('button', { name: 'Create Goal' }).click()
  await expect(goalDialog).toBeHidden()

  // Verify goal card is rendered
  const goalCard = page.locator('.space-y-4').filter({ hasText: 'Emergency Fund' })
  await expect(goalCard.first()).toBeVisible()
  await expect(page.getByText('Remaining: ₹50,000.00')).toBeVisible()

  // 6. Contribute 20,000.00 to the goal
  await page.getByRole('button', { name: 'Contribute to Emergency Fund' }).click()
  const contribDialog = page.getByRole('dialog')
  await expect(contribDialog).toBeVisible()

  await contribDialog.getByLabel('Amount (₹)').fill('20000.00')
  await contribDialog.getByRole('button', { name: 'Confirm' }).click()
  await expect(contribDialog).toBeHidden()

  // 7. Verify progress updates
  // Current amount is now 20,000 of 50,000 = 40% progress, remaining 30,000
  await expect(page.getByText('₹20,000.00')).toBeVisible()
  await expect(page.getByText('of ₹50,000.00')).toBeVisible()
  await expect(page.getByText('40.00%')).toBeVisible()
  await expect(page.getByText('Remaining: ₹30,000.00')).toBeVisible()
  const progressbar = page.getByRole('progressbar')
  await expect(progressbar).toHaveAttribute('aria-valuenow', '40')
})
