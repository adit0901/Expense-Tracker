import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { THEME_STORAGE_KEY, ThemeProvider, useTheme } from './theme'

function Toggle() {
  const { theme, setTheme } = useTheme()
  return (
    <>
      <span data-testid="theme">{theme}</span>
      <button onClick={() => setTheme('dark')}>dark</button>
      <button onClick={() => setTheme('light')}>light</button>
    </>
  )
}

test('theme preference toggles the root class and persists', async () => {
  const user = userEvent.setup()
  render(<ThemeProvider><Toggle /></ThemeProvider>)
  expect(document.documentElement).not.toHaveClass('dark')
  await user.click(screen.getByText('dark'))
  expect(document.documentElement).toHaveClass('dark')
  expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe('dark')
  await user.click(screen.getByText('light'))
  expect(document.documentElement).not.toHaveClass('dark')
  expect(screen.getByTestId('theme')).toHaveTextContent('light')
})

test('stored preference is applied on start', () => {
  localStorage.setItem(THEME_STORAGE_KEY, 'dark')
  render(<ThemeProvider><Toggle /></ThemeProvider>)
  expect(document.documentElement).toHaveClass('dark')
})
