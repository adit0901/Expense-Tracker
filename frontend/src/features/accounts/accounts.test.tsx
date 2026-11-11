import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'

import { ACCOUNT } from '@/test/fixtures'
import { API, server } from '@/test/server'
import { renderApp } from '@/test/utils'

test('lists accounts with balances and the liquid funds summary', async () => {
  renderApp('/settings/accounts')
  expect(await screen.findByText('HDFC Savings')).toBeInTheDocument()
  expect(screen.getByText('₹1,18,000.00')).toBeInTheDocument()
  expect(screen.getByText('Outstanding')).toBeInTheDocument()
  expect(screen.getByText('₹1,20,000.00')).toBeInTheDocument()
})

test('create account posts the form and shows last-4 validation', async () => {
  let body: Record<string, unknown> | null = null
  server.use(http.post(`${API}/accounts`, async ({ request }) => {
    body = (await request.json()) as Record<string, unknown>
    return HttpResponse.json({ data: { ...ACCOUNT, id: 'new', name: body.name }, meta: {} }, { status: 201 })
  }))
  const user = userEvent.setup()
  renderApp('/settings/accounts')
  await user.click(await screen.findByRole('button', { name: /add account/i }))
  const dialog = await screen.findByRole('dialog')
  await user.type(within(dialog).getByLabelText('Name'), 'Cash Wallet')
  await user.type(within(dialog).getByLabelText('Last 4 digits (optional)'), '123456')
  await user.clear(within(dialog).getByLabelText('Opening balance (₹)'))
  await user.type(within(dialog).getByLabelText('Opening balance (₹)'), '2500.50')
  await user.click(within(dialog).getByRole('button', { name: 'Add account' }))
  expect(await within(dialog).findByText(/last 4 digits/i, { selector: 'p' })).toBeInTheDocument()
  expect(body).toBeNull()
  await user.clear(within(dialog).getByLabelText('Last 4 digits (optional)'))
  await user.type(within(dialog).getByLabelText('Last 4 digits (optional)'), '4321')
  await user.click(within(dialog).getByRole('button', { name: 'Add account' }))
  await waitFor(() => expect(body).toMatchObject({ name: 'Cash Wallet', type: 'bank', last4: '4321', opening_balance: '2500.50' }))
})

test('archive asks for confirmation before calling the API', async () => {
  let archived = false
  server.use(http.post(`${API}/accounts/acc-1/archive`, () => {
    archived = true
    return HttpResponse.json({ data: { ...ACCOUNT, archived_at: '2026-11-11T00:00:00Z' }, meta: {} })
  }))
  const user = userEvent.setup()
  renderApp('/settings/accounts')
  await user.click(await screen.findByRole('button', { name: 'Archive HDFC Savings' }))
  const dialog = await screen.findByRole('alertdialog')
  expect(within(dialog).getByText(/history stays in reports/i)).toBeInTheDocument()
  expect(archived).toBe(false)
  await user.click(within(dialog).getByRole('button', { name: 'Archive' }))
  await waitFor(() => expect(archived).toBe(true))
})

test('deleting an account with history offers archiving', async () => {
  server.use(http.delete(`${API}/accounts/acc-1`, () => HttpResponse.json({
    error: { code: 'account_has_transactions', message: 'This account has transactions and cannot be deleted. Archive it instead.', details: [] },
  }, { status: 409 })))
  const user = userEvent.setup()
  renderApp('/settings/accounts')
  await user.click(await screen.findByRole('button', { name: 'Delete HDFC Savings' }))
  await user.click(within(await screen.findByRole('alertdialog')).getByRole('button', { name: 'Delete' }))
  expect(await screen.findByRole('heading', { name: 'Archive HDFC Savings?' })).toBeInTheDocument()
})
