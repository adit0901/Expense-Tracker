import { formatChange, formatDate, formatMoney, formatPercent } from './format'

describe('formatMoney', () => {
  it('uses Indian lakh/crore grouping', () => {
    expect(formatMoney('1234567.89', { grouping: 'indian' })).toBe('₹12,34,567.89')
    expect(formatMoney('123456789.00', { grouping: 'indian' })).toBe('₹12,34,56,789.00')
  })
  it('uses international thousands grouping', () => {
    expect(formatMoney('1234567.89', { grouping: 'international' })).toBe('₹1,234,567.89')
  })
  it('keeps exact decimals from strings and handles negatives', () => {
    expect(formatMoney('0.60')).toBe('₹0.60')
    expect(formatMoney('-15000.00')).toBe('-₹15,000.00')
    expect(formatMoney(null)).toBe('—')
  })
})

describe('other formatters', () => {
  it('formats percentages and N/A', () => {
    expect(formatPercent('25.00')).toBe('25.00%')
    expect(formatPercent(null)).toBe('N/A')
  })
  it('formats changes with a dash for not-applicable', () => {
    expect(formatChange('20.00', 'percent')).toBe('+20.00%')
    expect(formatChange('-14.50', 'points')).toBe('-14.50 pts')
    expect(formatChange(null, 'percent')).toBe('—')
  })
  it('formats dates by preference', () => {
    expect(formatDate('2026-10-05')).toBe('05/10/2026')
    expect(formatDate('2026-10-05', 'MM/DD/YYYY')).toBe('10/05/2026')
    expect(formatDate('2026-10-05', 'YYYY-MM-DD')).toBe('2026-10-05')
  })
})
