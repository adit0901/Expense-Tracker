import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'

import { API, server } from '@/test/server'
import { renderApp } from '@/test/utils'

test('preferences show number grouping examples with Indian grouping', async () => {
  renderApp('/settings/preferences')
  expect(await screen.findByText('INR (Indian Rupee)')).toBeInTheDocument()
  expect(screen.getByLabelText('Number grouping')).toHaveTextContent('₹12,34,567.89')
})

test('changing email reveals and sends the current password', async () => {
  let body: Record<string, unknown> = {}
  server.use(http.patch(`${API}/users/me`, async ({ request }) => {
    body = (await request.json()) as Record<string, unknown>
    return HttpResponse.json({ data: { id: 'u', email: body.email, full_name: body.full_name, created_at: '' }, meta: {} })
  }))
  const user = userEvent.setup()
  renderApp('/settings/profile')
  const email = await screen.findByLabelText('Email')
  await waitFor(() => expect(email).toHaveValue('asha@example.com'))
  expect(screen.queryByLabelText('Current password')).not.toBeInTheDocument()
  await user.clear(email)
  await user.type(email, 'new@example.com')
  await user.type(await screen.findByLabelText('Current password'), 'Correct-Horse-1')
  await user.click(screen.getByRole('button', { name: /save profile/i }))
  await waitFor(() => expect(body).toEqual({ full_name: 'Asha Rao', email: 'new@example.com', current_password: 'Correct-Horse-1' }))
})

test('account deletion requires confirmation with password', async () => {
  let deleted: unknown = null
  server.use(http.delete(`${API}/users/me`, async ({ request }) => {
    deleted = await request.json()
    return new HttpResponse(null, { status: 204 })
  }))
  const user = userEvent.setup()
  const { router } = renderApp('/settings/delete')
  await user.click(await screen.findByRole('button', { name: 'Delete my account' }))
  const confirm = await screen.findByRole('button', { name: 'Delete account permanently' })
  expect(screen.getByText('asha@example.com')).toBeInTheDocument()
  expect(confirm).toBeDisabled()
  await user.type(screen.getByLabelText('Enter your password to confirm'), 'Correct-Horse-1')
  await user.click(confirm)
  await waitFor(() => expect(deleted).toEqual({ password: 'Correct-Horse-1' }))
  await waitFor(() => expect(router.state.location.pathname).toBe('/login'))
  expect(router.state.location.search).toBe('')
})
