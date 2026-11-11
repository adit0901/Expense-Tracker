import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'

import { API, server } from '@/test/server'
import { renderApp } from '@/test/utils'

test('shows subcategories, essential flags and protects system categories', async () => {
  renderApp('/settings/categories')
  const list = await screen.findByRole('list', { name: 'expense categories' })
  expect(within(list).getByText('Groceries')).toBeInTheDocument()
  expect(within(list).getByRole('switch', { name: 'Food is essential' })).toBeChecked()
  expect(within(list).queryByRole('button', { name: 'Delete Loan Interest' })).not.toBeInTheDocument()
  expect(within(list).queryByRole('button', { name: 'Add subcategory under Groceries' })).not.toBeInTheDocument()
})

test('delete with replacement: in-use category asks for a replacement and reassigns', async () => {
  const calls: string[] = []
  server.use(http.delete(`${API}/categories/cat-ent`, ({ request }) => {
    const replacement = new URL(request.url).searchParams.get('replacement_id')
    calls.push(replacement ?? '')
    if (!replacement) {
      return HttpResponse.json({ error: { code: 'category_in_use', message: 'This category has transactions.', details: [] } }, { status: 409 })
    }
    return HttpResponse.json({ data: { deleted_ids: ['cat-ent'], reassigned_transactions: 3, replacement_id: replacement }, meta: {} })
  }))
  const user = userEvent.setup()
  renderApp('/settings/categories')
  await user.click(await screen.findByRole('button', { name: 'Delete Entertainment' }))
  let dialog = await screen.findByRole('alertdialog')
  await user.click(within(dialog).getByRole('button', { name: 'Delete' }))
  dialog = await screen.findByRole('alertdialog')
  expect(await within(dialog).findByRole('alert')).toHaveTextContent('Choose a category to move them to')
  const confirm = within(dialog).getByRole('button', { name: 'Move transactions and delete' })
  expect(confirm).toBeDisabled()
  const select = within(dialog).getByLabelText('Replacement category')
  expect(within(select).queryByRole('option', { name: 'Entertainment' })).not.toBeInTheDocument()
  expect(within(select).queryByRole('option', { name: 'Salary' })).not.toBeInTheDocument()
  await user.selectOptions(select, 'cat-others')
  await user.click(confirm)
  await waitFor(() => expect(calls).toEqual(['', 'cat-others']))
  await waitFor(() => expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument())
})
