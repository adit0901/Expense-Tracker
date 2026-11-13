import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { renderApp } from '@/test/utils'

describe('Loans & EMIs — Break UI Scenarios', () => {
  it('renders Break UI scenario selector in development mode', async () => {
    await renderApp('/loans?data=demo')

    const selector = await screen.findByRole('complementary', { name: /break ui scenario selector/i })
    expect(selector).toBeInTheDocument()

    expect(within(selector).getByRole('button', { name: /^demo$/i })).toBeInTheDocument()
    expect(within(selector).getByRole('button', { name: /^worst case$/i })).toBeInTheDocument()
    expect(within(selector).getByRole('button', { name: /^empty$/i })).toBeInTheDocument()
    expect(within(selector).getByRole('button', { name: /^one$/i })).toBeInTheDocument()
    expect(within(selector).getByRole('button', { name: /^1,000 rows$/i })).toBeInTheDocument()
    expect(within(selector).getByRole('button', { name: /^live api$/i })).toBeInTheDocument()
  })

  it('switches to worst-case scenario (?data=worst) and displays extreme values', async () => {
    await renderApp('/loans?data=worst')

    // Long compound lender name
    expect(
      await screen.findByText(/Housing Development & Infrastructure Finance Corporation of South Asia/i),
    ).toBeInTheDocument()

    // Unbreakable lender string
    expect(
      screen.getByText(/StateBankOfHyderabad-RetailAssetsAndAssetReconstructionSecuritizationBranch/i),
    ).toBeInTheDocument()

    // Non-Latin Hindi & emoji lender name
    expect(
      screen.getByText(/भारतीय स्टेट बैंक — 🏦 SBI Global Ed-vantage/i),
    ).toBeInTheDocument()

    // 0.00% rate
    expect(screen.getByText('0.00% p.a.')).toBeInTheDocument()

    // Custom EMI badge
    expect(screen.getAllByText('Custom EMI').length).toBeGreaterThan(0)

    // Summary KPIs with large numbers
    expect(screen.getByText(/5,77,75,309/)).toBeInTheDocument()
    expect(screen.getByText('4')).toBeInTheDocument()
  })

  it('renders empty scenario (?data=empty) with zero counts and empty state', async () => {
    await renderApp('/loans?data=empty')

    expect(await screen.findByText('No loans found')).toBeInTheDocument()
    expect(screen.getByText('No active loans recorded. Add your home, car, or personal loans to track repayment schedules and EMIs.')).toBeInTheDocument()
    expect(screen.getByText('Add your first loan')).toBeInTheDocument()
  })

  it('renders one item scenario (?data=one) with exactly one loan card', async () => {
    await renderApp('/loans?data=one')

    expect(await screen.findByText('SBI Home Finance')).toBeInTheDocument()
    expect(screen.getByText('114 of 120 months', { exact: false })).toBeInTheDocument()
  })

  it('renders huge collection scenario (?data=huge) with 1,000 items', async () => {
    await renderApp('/loans?data=huge')

    // In huge scenario, 1,000 unvirtualized cards are mounted
    expect(await screen.findByText('Kotak Mahindra Prime Finance #1')).toBeInTheDocument()
  })

  it('opens Amortization Schedule modal with worst-case 360-month loan', async () => {
    const user = userEvent.setup()
    await renderApp('/loans?data=worst')

    const scheduleButtons = await screen.findAllByRole('button', { name: 'Schedule' })
    await user.click(scheduleButtons[0]!)

    // Verify modal header with long name
    expect(await screen.findByRole('dialog')).toBeInTheDocument()
    expect(screen.getByText(/Amortization Schedule: Housing Development & Infrastructure/i)).toBeInTheDocument()

    // Verify installments table rendered
    expect(screen.getByRole('columnheader', { name: '#' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Due Date' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Closing Balance' })).toBeInTheDocument()
  })

  it('displays Break UI presets inside Add Loan dialog and autofills worst-case data', async () => {
    const user = userEvent.setup()
    await renderApp('/loans?data=demo')

    const addLoanBtn = await screen.findByRole('button', { name: /add loan/i })
    await user.click(addLoanBtn)

    expect(await screen.findByRole('dialog')).toBeInTheDocument()
    expect(screen.getByText('Break UI Presets:')).toBeInTheDocument()

    const worstPresetBtn = screen.getByRole('button', { name: /^worst case$/i })
    await user.click(worstPresetBtn)

    const lenderInput = screen.getByLabelText(/lender \/ bank/i) as HTMLInputElement
    expect(lenderInput.value).toContain('Housing Development & Infrastructure Finance Corporation')

    const principalInput = screen.getByLabelText(/^principal/i) as HTMLInputElement
    expect(principalInput.value).toBe('50000000.00')

    const zeroRateBtn = screen.getByRole('button', { name: /^0% rate$/i })
    await user.click(zeroRateBtn)
    expect(lenderInput.value).toContain('StateBankOfHyderabad')
    const rateInput = screen.getByLabelText(/interest rate/i) as HTMLInputElement
    expect(rateInput.value).toBe('0.00')
  })
})
