import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'

import type { ImportBatchOut, ImportRowOut } from '@/services/api/types'
import { API, server } from '@/test/server'
import { renderApp } from '@/test/utils'
import * as client from '@/services/api/client'

function row(n: number, extra: Partial<ImportRowOut> = {}): ImportRowOut {
  return { row: n, date: '2026-10-05', type: 'expense', amount: '450.00', description: `Row ${n}`, payee: null,
    category_id: 'cat-food', category_name: 'Food', payment_method: 'upi', errors: [], warnings: [],
    duplicate: false, duplicate_of: [], selected: true, ...extra }
}

const BATCH: ImportBatchOut = {
  id: 'imp-1', status: 'preview', file_name: 'bank.csv', account_id: 'acc-1', encoding: 'utf-8',
  date_format: 'DD/MM/YYYY', headers: ['Date', 'Amount', 'Description'],
  column_mapping: { date: 'Date', amount: 'Amount', description: 'Description' },
  row_count: 4, valid_count: 3, invalid_count: 1, duplicate_count: 1, imported_count: 0,
  rows: [
    row(2),
    row(3, { date: null, amount: '10.00', errors: ["invalid date '31/02/2026' (expected DD/MM/YYYY)"], selected: false }),
    row(4, { duplicate: true, duplicate_of: ['txn-1'], selected: false, description: 'Swiggy order' }),
    row(5, { category_name: 'Others', warnings: ["unknown category 'Gadgets', using 'Others'"] }),
  ],
  created_at: '2026-11-11T00:00:00Z', confirmed_at: null, undone_at: null, undo_available_until: null,
}

async function uploadAndPreview(user: ReturnType<typeof userEvent.setup>) {
  renderApp('/transactions/import')
  await user.upload(await screen.findByLabelText(/CSV file/), new File(['Date,Amount\n'], 'bank.csv', { type: 'text/csv' }))
  await waitFor(() => expect(screen.getAllByRole('option', { name: 'HDFC Savings' }).length).toBeGreaterThan(0))
  await user.selectOptions(screen.getByLabelText('Import into account'), 'acc-1')
  await user.click(screen.getByRole('button', { name: 'Preview' }))
}

test('preview shows errors, warnings and leaves duplicates unselected', async () => {
  server.use(http.post(`${API}/imports`, () => HttpResponse.json({ data: BATCH, meta: {} }, { status: 201 })))
  const user = userEvent.setup()
  await uploadAndPreview(user)
  expect(await screen.findByText(/4 rows · 3 valid · 1 with errors · 1 possible duplicates/)).toBeInTheDocument()
  expect(screen.getByRole('checkbox', { name: 'Import row 2' })).toBeChecked()
  const invalid = screen.getByRole('checkbox', { name: 'Import row 3' })
  expect(invalid).toBeDisabled()
  expect(invalid).not.toBeChecked()
  expect(screen.getByText(/invalid date/)).toBeInTheDocument()
  expect(screen.getByRole('checkbox', { name: 'Import row 4' })).not.toBeChecked()
  expect(screen.getByText('Possible duplicate')).toBeInTheDocument()
  expect(screen.getByText(/unknown category 'Gadgets'/)).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Import 2 selected rows' })).toBeEnabled()
  expect(screen.getByLabelText('Date')).toHaveValue('Date')
})

test('confirm sends selected rows (duplicate included only when ticked) and undo asks first', async () => {
  let confirmed: unknown = null
  let undone = false
  server.use(
    http.post(`${API}/imports`, () => HttpResponse.json({ data: BATCH, meta: {} }, { status: 201 })),
    http.post(`${API}/imports/imp-1/confirm`, async ({ request }) => {
      confirmed = await request.json()
      return HttpResponse.json({ data: { ...BATCH, status: 'confirmed', imported_count: 3, confirmed_at: '2026-11-11T00:00:00Z',
        undo_available_until: '2026-11-12T00:00:00Z' }, meta: {} })
    }),
    http.post(`${API}/imports/imp-1/undo`, () => {
      undone = true
      return HttpResponse.json({ data: { ...BATCH, status: 'undone', imported_count: 3 }, meta: {} })
    }),
  )
  const user = userEvent.setup()
  await uploadAndPreview(user)
  await user.click(await screen.findByRole('checkbox', { name: 'Import row 4' }))
  await user.click(screen.getByRole('button', { name: 'Import 3 selected rows' }))
  await waitFor(() => expect(confirmed).toEqual({ selected_rows: [2, 4, 5] }))
  expect(await screen.findByText(/Imported 3 transactions from bank.csv/)).toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'Undo import' }))
  const dialog = await screen.findByRole('alertdialog')
  expect(within(dialog).getByText(/deletes all 3 transactions/)).toBeInTheDocument()
  expect(undone).toBe(false)
  await user.click(within(dialog).getByRole('button', { name: 'Undo import' }))
  await waitFor(() => expect(undone).toBe(true))
  expect(await screen.findByText(/This import was undone/)).toBeInTheDocument()
})

test('unknown columns prompt for a manual mapping', async () => {
  const sent: (string | null)[] = []
  const spy = vi.spyOn(client.api, 'post')
  let calls = 0
  server.use(http.post(`${API}/imports`, () => {
    calls += 1
    if (calls === 1) {
      return HttpResponse.json({ error: { code: 'invalid_mapping', message: 'Column mapping is incomplete',
        details: [{ field: 'column_mapping', message: 'incomplete', headers: ['Txn', 'Value'], suggested: {} }] } }, { status: 422 })
    }
    return HttpResponse.json({ data: BATCH, meta: {} }, { status: 201 })
  }))
  const user = userEvent.setup()
  await uploadAndPreview(user)
  expect(await screen.findByText(/Map them below/)).toBeInTheDocument()
  await user.selectOptions(screen.getByLabelText('Date'), 'Txn')
  await user.selectOptions(screen.getByLabelText('Amount (signed or with type)'), 'Value')
  await user.click(screen.getByRole('button', { name: 'Preview with this mapping' }))
  expect(await screen.findByText(/4 rows/)).toBeInTheDocument()
  for (const [path, body] of spy.mock.calls) {
    if (path === '/imports') sent.push((body as FormData).get('column_mapping') as string | null)
  }
  expect(sent).toEqual([null, JSON.stringify({ date: 'Txn', amount: 'Value' })])
  spy.mockRestore()
})
