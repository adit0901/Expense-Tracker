import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'

import { addAccount, addTransaction, register } from './helpers'

test('375 px: navigation via menu button and no horizontal page scroll', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 })
  await register(page)
  await addAccount(page, 'HDFC Savings', '1000.00')
  await addTransaction(page, { account: 'HDFC Savings', category: 'Food', amount: '450.00', method: 'UPI', description: 'A fairly long description for a narrow screen' })
  for (const path of ['/transactions', '/', '/reports', '/settings/accounts', '/budgets']) {
    await page.goto(path)
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
    expect(overflow, `horizontal page scroll on ${path}`).toBeLessThanOrEqual(0)
  }
  await page.goto('/transactions')
  await expect(page.getByRole('navigation', { name: 'Main navigation' })).toBeHidden()
  await page.getByRole('button', { name: 'Open navigation menu' }).click()
  await page.getByRole('dialog').getByRole('link', { name: /^Reports & Analytics/ }).click()
  await expect(page.getByRole('heading', { name: 'Reports & Analytics' })).toBeVisible()
})

const PAGES = ['/', '/transactions', '/income', '/expenses', '/reports', '/settings/profile',
  '/settings/preferences', '/settings/accounts', '/settings/categories', '/budgets', '/transactions/import']

for (const theme of ['light', 'dark'] as const) {
  test(`axe: no serious or critical violations (${theme} theme)`, async ({ page }) => {
    await page.emulateMedia({ colorScheme: theme })
    await register(page)
    await addAccount(page, 'HDFC Savings', '1000.00')
    await addTransaction(page, { account: 'HDFC Savings', category: 'Food', amount: '450.00', method: 'UPI', description: 'Dinner' })
    expect(await page.evaluate(() => document.documentElement.classList.contains('dark'))).toBe(theme === 'dark')
    const failures: string[] = []
    for (const path of PAGES) {
      await page.goto(path)
      await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
      await page.waitForLoadState('networkidle')
      const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze()
      for (const v of results.violations.filter((x) => x.impact === 'serious' || x.impact === 'critical')) {
        failures.push(`${path}: ${v.id} (${v.impact}) — ${v.nodes.slice(0, 3).map((n) => n.target.join(' ')).join(', ')}`)
      }
    }
    // Public auth pages too.
    await page.getByRole('button', { name: 'Sign out' }).click()
    for (const path of ['/login', '/register', '/forgot-password']) {
      await page.goto(path)
      const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze()
      for (const v of results.violations.filter((x) => x.impact === 'serious' || x.impact === 'critical')) {
        failures.push(`${path}: ${v.id} (${v.impact}) — ${v.nodes.slice(0, 3).map((n) => n.target.join(' ')).join(', ')}`)
      }
    }
    expect(failures).toEqual([])
  })
}

test('keyboard: transaction form fields receive visible focus in order', async ({ page }) => {
  await register(page)
  await addAccount(page, 'HDFC Savings', '0.00')
  await page.goto('/transactions')
  await page.getByRole('button', { name: 'Add transaction' }).first().click()
  const dialog = page.getByRole('dialog')
  await dialog.getByLabel('Expense', { exact: true }).focus()
  const order: string[] = []
  for (let i = 0; i < 9; i++) {
    await page.keyboard.press('Tab')
    await page.waitForTimeout(300) // let the focus-ring transition finish
    order.push(await page.evaluate(() => {
      const el = document.activeElement as HTMLElement | null
      const label = el?.id ? document.querySelector(`label[for="${el.id}"]`)?.textContent : null
      const style = el ? getComputedStyle(el) : null
      // A date input's calendar button is its own Tab stop inside the shadow DOM; its focus
      // outline comes from the ::-webkit-calendar-picker-indicator:focus-visible rule in
      // index.css (getComputedStyle can't observe pseudo-element focus state).
      const pickerStop = el instanceof HTMLInputElement && el.type === 'date' && !el.matches(':focus')
      const visible = pickerStop || (!!style && (style.outlineStyle !== 'none' || style.boxShadow !== 'none'))
      return `${label ?? el?.getAttribute('aria-label') ?? el?.textContent?.trim() ?? el?.tagName}|${visible}`
    }))
  }
  const labels = order.map((o) => o.split('|')[0])
  expect(labels).toEqual(expect.arrayContaining(['Account', 'Category', 'Amount (₹)', 'Date', 'Payment method']))
  expect(labels.indexOf('Account')).toBeLessThan(labels.indexOf('Amount (₹)'))
  expect(order.filter((o) => o.endsWith('|false'))).toEqual([])
})
