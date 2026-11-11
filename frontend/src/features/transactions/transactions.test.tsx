import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'

import { txn } from '@/test/fixtures'
import { API, db, requests, server } from '@/test/server'
import { renderApp } from '@/test/utils'

import { filtersFromSearch, filtersToApiQuery, filtersToSearch } from './filters'

const lastTxnQuery = () => {
  const r = [...requests].reverse().find((x) => x.path === '/transactions' && x.method === 'GET' && !x.search.includes('page_size=10'))
  return new URLSearchParams(r?.search ?? '')
}

test('filter mapping round-trips URL <-> API query', () => {
  const p = new URLSearchParams('date_from=2026-10-01&date_to=2026-10-31&type=expense&category_id=cat-food&q=swiggy&page=2')
  const f = filtersFromSearch(p)
  expect(f).toEqual({ date_from: '2026-10-01', date_to: '2026-10-31', type: ['expense'], category_id: 'cat-food', q: 'swiggy', page: 2 })
  const sorted = (x: URLSearchParams) => [...x.entries()].sort()
  expect(sorted(filtersToSearch(f))).toEqual(sorted(p))
  expect(filtersToApiQuery(f)).toMatchObject({ category_id: 'cat-food', type: ['expense'], page: 2, page_size: 25 })
})

test('drill-down URL params are sent to the API', async () => {
  renderApp('/transactions?category_id=cat-food&type=expense&date_from=2026-11-01&date_to=2026-11-30')
  expect(await screen.findByText('Dinner')).toBeInTheDocument()
  const q = lastTxnQuery()
  expect(q.get('category_id')).toBe('cat-food')
  expect(q.getAll('type')).toEqual(['expense'])
  expect(q.get('date_from')).toBe('2026-11-01')
  expect(q.get('page_size')).toBe('25')
})

test('changing filters updates the URL and the API query', async () => {
  const user = userEvent.setup()
  const { router } = renderApp('/transactions')
  await screen.findByText('Dinner')
  await user.selectOptions(screen.getByLabelText('Payment method'), 'upi')
  await user.selectOptions(screen.getByLabelText('Type'), 'expense')
  await user.type(screen.getByLabelText('Search'), 'swiggy{enter}')
  await waitFor(() => expect(lastTxnQuery().get('q')).toBe('swiggy'))
  const q = lastTxnQuery()
  expect(q.get('payment_method')).toBe('upi')
  expect(q.getAll('type')).toEqual(['expense'])
  expect(router.state.location.search).toContain('payment_method=upi')
  await user.click(screen.getByRole('button', { name: 'Clear' }))
  await waitFor(() => expect(router.state.location.search).toBe(''))
})

test('empty state when no transactions match', async () => {
  db.transactions = []
  renderApp('/transactions?q=nothing')
  expect(await screen.findByText('No transactions found')).toBeInTheDocument()
})

test('delete confirmation shows date, amount and description', async () => {
  let deleted = false
  server.use(http.delete(`${API}/transactions/txn-1`, () => {
    deleted = true
    return new HttpResponse(null, { status: 204 })
  }))
  const user = userEvent.setup()
  renderApp('/transactions')
  await user.click(await screen.findByRole('button', { name: 'Delete Dinner' }))
  const dialog = await screen.findByRole('alertdialog')
  expect(within(dialog).getByText('10/11/2026')).toBeInTheDocument()
  expect(within(dialog).getByText(/₹450.00/)).toBeInTheDocument()
  expect(within(dialog).getByText('Dinner')).toBeInTheDocument()
  await user.click(within(dialog).getByRole('button', { name: 'Delete' }))
  await waitFor(() => expect(deleted).toBe(true))
})

async function openForm(user: ReturnType<typeof userEvent.setup>) {
  renderApp('/transactions')
  await user.click(await screen.findByRole('button', { name: /add transaction/i }))
  return screen.findByRole('dialog')
}

test('duplicate warning lets the user confirm and resubmits with confirm_duplicate', async () => {
  const bodies: Record<string, unknown>[] = []
  server.use(http.post(`${API}/transactions`, async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>
    bodies.push(body)
    if (!body.confirm_duplicate) {
      return HttpResponse.json({ error: { code: 'possible_duplicate', message: 'Possible duplicate', details: [
        { candidate: { id: 'txn-1', txn_date: '2026-11-10', amount: '450.00', type: 'expense', payee: 'Swiggy', description: 'Dinner' } },
      ] } }, { status: 409 })
    }
    return HttpResponse.json({ data: txn({ id: 'txn-2' }), meta: {} }, { status: 201 })
  }))
  const user = userEvent.setup()
  const dialog = await openForm(user)
  await waitFor(() => expect(within(dialog).getAllByRole('option', { name: 'HDFC Savings' }).length).toBeGreaterThan(0))
  await user.selectOptions(within(dialog).getByLabelText('Account'), 'acc-1')
  await user.selectOptions(within(dialog).getByLabelText('Category'), 'cat-food')
  await user.type(within(dialog).getByLabelText('Amount (₹)'), '450.00')
  await user.selectOptions(within(dialog).getByLabelText('Payment method'), 'upi')
  await user.type(within(dialog).getByLabelText('Payee (optional)'), 'Swiggy')
  await user.click(within(dialog).getByRole('button', { name: 'Save transaction' }))
  const warning = await within(dialog).findByText(/possible duplicate of/i)
  expect(warning.parentElement).toHaveTextContent('Swiggy')
  expect(bodies).toHaveLength(1)
  await user.click(within(dialog).getByRole('button', { name: 'Save anyway' }))
  await waitFor(() => expect(bodies).toHaveLength(2))
  expect(bodies[1]).toMatchObject({ confirm_duplicate: true, amount: '450.00', category_id: 'cat-food', payment_method: 'upi' })
  await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
})

test('salary breakdown mismatch is shown next to gross and values are kept', async () => {
  server.use(http.post(`${API}/transactions`, () => HttpResponse.json({
    error: { code: 'salary_breakdown_mismatch', message: 'Gross minus deductions (123000.00) does not equal the credited amount (125000.00)',
      details: [{ field: 'salary_breakdown', message: 'mismatch', expected_net: '123000.00', amount: '125000.00' }] },
  }, { status: 422 })))
  const user = userEvent.setup()
  const dialog = await openForm(user)
  await user.click(within(dialog).getByLabelText('Income'))
  await waitFor(() => expect(within(dialog).getAllByRole('option', { name: 'HDFC Savings' }).length).toBeGreaterThan(0))
  await user.selectOptions(within(dialog).getByLabelText('Account'), 'acc-1')
  await user.selectOptions(within(dialog).getByLabelText('Category'), 'cat-salary')
  await user.type(within(dialog).getByLabelText('Amount (₹)'), '125000.00')
  await user.click(within(dialog).getByLabelText('Record gross salary and deductions'))
  await user.type(within(dialog).getByLabelText('Gross salary (₹)'), '150000.00')
  await user.click(within(dialog).getByRole('button', { name: 'Add deduction' }))
  await user.type(within(dialog).getByLabelText('Deduction 1 name'), 'Income Tax/TDS')
  await user.type(within(dialog).getByLabelText('Amount'), '27000.00')
  await user.click(within(dialog).getByRole('button', { name: 'Save transaction' }))
  const gross = within(dialog).getByLabelText('Gross salary (₹)')
  await waitFor(() => expect(gross).toHaveAttribute('aria-invalid', 'true'))
  expect(within(dialog).getByText(/Gross minus deductions is ₹1,23,000.00/)).toBeInTheDocument()
  expect(gross).toHaveValue('150000.00')
  expect(within(dialog).getByLabelText('Amount (₹)')).toHaveValue('125000.00')
})

test('server field errors appear next to the field and keep values', async () => {
  server.use(http.post(`${API}/transactions`, () => HttpResponse.json({
    error: { code: 'payment_method_account_mismatch', message: 'Credit card payments must use a credit card account',
      details: [{ field: 'payment_method', message: 'account_mismatch' }] },
  }, { status: 422 })))
  const user = userEvent.setup()
  const dialog = await openForm(user)
  await waitFor(() => expect(within(dialog).getAllByRole('option', { name: 'HDFC Savings' }).length).toBeGreaterThan(0))
  await user.selectOptions(within(dialog).getByLabelText('Account'), 'acc-1')
  await user.selectOptions(within(dialog).getByLabelText('Category'), 'cat-food')
  await user.type(within(dialog).getByLabelText('Amount (₹)'), '10')
  await user.selectOptions(within(dialog).getByLabelText('Payment method'), 'credit_card')
  await user.click(within(dialog).getByRole('button', { name: 'Save transaction' }))
  const method = within(dialog).getByLabelText('Payment method')
  await waitFor(() => expect(method).toHaveAttribute('aria-invalid', 'true'))
  expect(within(dialog).getAllByText('Credit card payments must use a credit card account').length).toBeGreaterThan(0)
  expect(method).toHaveValue('credit_card')
  expect(within(dialog).getByLabelText('Amount (₹)')).toHaveValue('10')
})

test('transfer form hides category and validates distinct accounts', async () => {
  const user = userEvent.setup()
  const dialog = await openForm(user)
  await user.click(within(dialog).getByLabelText('Transfer'))
  expect(within(dialog).queryByLabelText('Category')).not.toBeInTheDocument()
  await waitFor(() => expect(within(dialog).getAllByRole('option', { name: 'HDFC Savings' }).length).toBeGreaterThan(0))
  await user.selectOptions(within(dialog).getByLabelText('From account'), 'acc-1')
  await user.selectOptions(within(dialog).getByLabelText('To account'), 'acc-1')
  await user.type(within(dialog).getByLabelText('Amount (₹)'), '100')
  await user.click(within(dialog).getByRole('button', { name: 'Save transaction' }))
  expect(await within(dialog).findByText('Source and destination must differ')).toBeInTheDocument()
})
