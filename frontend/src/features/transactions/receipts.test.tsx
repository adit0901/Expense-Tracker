import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'

import { ThemeProvider } from '@/app/theme'
import { txn } from '@/test/fixtures'
import { API, server } from '@/test/server'

import { Receipts, uploadErrorMessage } from './Receipts'
import { ApiError } from '@/services/api/client'

function renderReceipts(attachments = 0) {
  const t = txn({ attachments: Array.from({ length: attachments }, (_, i) => ({
    id: `att-${i}`, original_name: `r${i}.png`, mime_type: 'image/png', size_bytes: 2048, created_at: '' })) })
  render(<QueryClientProvider client={new QueryClient()}><ThemeProvider><Receipts transaction={t} /></ThemeProvider></QueryClientProvider>)
}

test('rejects a disguised executable with a clear message', async () => {
  server.use(http.post(`${API}/transactions/txn-1/attachments`, () => HttpResponse.json({
    error: { code: 'unsupported_file_type', message: 'Only PDF, JPEG, PNG and WebP receipts are allowed', details: [] } }, { status: 422 })))
  const user = userEvent.setup({ applyAccept: false })
  renderReceipts()
  await user.upload(screen.getByLabelText('Attach a receipt'), new File(['MZ...'], 'receipt.png', { type: 'image/png' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Only PDF, JPEG, PNG or WebP receipts can be uploaded.')
})

test('files over 10 MB are rejected before upload', async () => {
  const user = userEvent.setup()
  renderReceipts()
  const big = new File([new Uint8Array(10 * 1024 * 1024 + 1)], 'big.jpg', { type: 'image/jpeg' })
  await user.upload(screen.getByLabelText('Attach a receipt'), big)
  expect(await screen.findByRole('alert')).toHaveTextContent('larger than 10 MB')
})

test('upload is disabled at the 5-receipt limit and lists files', () => {
  renderReceipts(5)
  expect(screen.getByLabelText('Attach a receipt')).toBeDisabled()
  expect(screen.getByText('r4.png')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Download r0.png' })).toBeInTheDocument()
})

test('maps server errors to friendly messages', () => {
  expect(uploadErrorMessage(new ApiError(413, 'file_too_large', 'x'))).toBe('That file is larger than 10 MB.')
  expect(uploadErrorMessage(new ApiError(409, 'attachment_limit', 'x'))).toMatch('at most 5')
})

test('export button requests CSV with the current filters', async () => {
  let search = ''
  server.use(http.get(`${API}/transactions/export.csv`, ({ request }) => {
    search = new URL(request.url).search
    return new HttpResponse('date,type\n', { headers: { 'Content-Type': 'text/csv', 'Content-Disposition': 'attachment; filename="transactions.csv"' } })
  }))
  URL.createObjectURL = vi.fn(() => 'blob:x')
  URL.revokeObjectURL = vi.fn()
  const { renderApp } = await import('@/test/utils')
  const user = userEvent.setup()
  renderApp('/transactions?type=expense&q=swiggy')
  await user.click(await screen.findByRole('button', { name: /export csv/i }))
  await vi.waitFor(() => expect(search).toContain('q=swiggy'))
  expect(search).toContain('type=expense')
  expect(search).not.toContain('page_size')
})
