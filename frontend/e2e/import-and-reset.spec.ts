import { expect, test } from '@playwright/test'

import { PASSWORD, addAccount, addTransaction, register, uniqueEmail } from './helpers'

function today(): { iso: string; ddmmyyyy: string } {
  const iso = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kolkata' }).format(new Date())
  const [y, m, d] = iso.split('-')
  return { iso, ddmmyyyy: `${d}/${m}/${y}` }
}

test('CSV import flags a duplicate row, imports the rest, and can be undone', async ({ page }) => {
  await register(page)
  await addAccount(page, 'HDFC Savings', '0.00')
  const { ddmmyyyy } = today()
  await addTransaction(page, { account: 'HDFC Savings', category: 'Food', amount: '450.00', method: 'UPI', description: 'Swiggy order' })

  const csv = ['Date,Amount,Type,Description,Category,Method',
    `${ddmmyyyy},450.00,expense,Swiggy order,Food,UPI`,
    `${ddmmyyyy},120.00,expense,Uber ride,Travel,UPI`,
    `31/02/2026,10.00,expense,Bad date,Food,UPI`].join('\n')

  await page.goto('/transactions/import')
  await page.getByLabel(/CSV file/).setInputFiles({ name: 'bank.csv', mimeType: 'text/csv', buffer: Buffer.from(csv) })
  await page.getByLabel('Import into account').selectOption({ label: 'HDFC Savings' })
  await page.getByRole('button', { name: 'Preview' }).click()

  await expect(page.getByText(/3 rows · 2 valid · 1 with errors · 1 possible duplicates/)).toBeVisible()
  await expect(page.getByRole('checkbox', { name: 'Import row 2' })).not.toBeChecked() // duplicate
  await expect(page.getByRole('checkbox', { name: 'Import row 3' })).toBeChecked()
  await expect(page.getByRole('checkbox', { name: 'Import row 4' })).toBeDisabled() // invalid date
  await page.getByRole('button', { name: 'Import 1 selected row' }).click()
  await expect(page.getByText('Imported 1 transactions from bank.csv.')).toBeVisible()

  // Check the imported rows in a second tab (the wizard keeps its state in this one).
  const href = await page.getByRole('link', { name: 'View transactions' }).getAttribute('href')
  const tab = await page.context().newPage()
  await tab.goto(href!)
  await expect(tab.getByText('Uber ride')).toBeVisible()
  await expect(tab.getByText('1 transaction ·')).toBeVisible()

  await page.getByRole('button', { name: 'Undo import' }).click()
  await page.getByRole('alertdialog').getByRole('button', { name: 'Undo import' }).click()
  await expect(page.getByText(/This import was undone/)).toBeVisible()
  await tab.reload()
  await expect(tab.getByText('No transactions found')).toBeVisible()
})

test('password reset via the emailed link (Mailpit)', async ({ page, request }) => {
  const email = uniqueEmail('reset')
  await register(page, email)
  await page.getByRole('button', { name: 'Sign out' }).click()
  await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible()

  await page.getByRole('link', { name: 'Forgot your password?' }).click()
  await expect(page.getByRole('heading', { name: 'Reset your password' })).toBeVisible()
  await page.getByLabel('Email').fill(email)
  await page.getByRole('button', { name: 'Send reset link' }).click()
  await expect(page.getByRole('status')).toContainText('If an account exists')

  let link = ''
  await expect.poll(async () => {
    const res = await request.get(`http://localhost:8025/api/v1/search?query=${encodeURIComponent(`to:${email}`)}`)
    const found = (await res.json()) as { messages: { ID: string }[] }
    if (!found.messages.length) return ''
    const msg = (await (await request.get(`http://localhost:8025/api/v1/message/${found.messages[0]!.ID}`)).json()) as { Text: string }
    link = /https?:\/\/\S+reset-password\?token=\S+/.exec(msg.Text)?.[0] ?? ''
    return link
  }, { timeout: 15_000 }).toContain('token=')

  const newPassword = 'Brand-New-Secret-77'
  await page.goto(new URL(link).pathname + new URL(link).search)
  await expect(page.getByRole('heading', { name: 'Choose a new password' })).toBeVisible()
  await page.getByLabel('New password', { exact: true }).fill(newPassword)
  await page.getByLabel('Confirm new password').fill(newPassword)
  await page.getByRole('button', { name: 'Update password' }).click()
  await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible()

  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill(PASSWORD)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.getByRole('alert')).toContainText('Invalid email or password')
  await page.getByLabel('Password').fill(newPassword)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.getByRole('heading', { name: 'Overview' })).toBeVisible()
})
