import { useSearchParams } from 'react-router'
import type { BreakUIScenario } from './test-scenarios'

const VALID_SCENARIOS: readonly BreakUIScenario[] = ['demo', 'worst', 'empty', 'one', 'huge'] as const

export function useBreakUIScenario(): BreakUIScenario | null {
  // Only enabled in dev mode; in production, this always returns null
  if (!import.meta.env.DEV) {
    return null
  }

  try {
    // eslint-disable-next-line react-hooks/rules-of-hooks
    const [searchParams] = useSearchParams()
    const data = searchParams.get('data')
    if (data && VALID_SCENARIOS.includes(data as BreakUIScenario)) {
      return data as BreakUIScenario
    }
  } catch {
    // Fallback if rendered outside of React Router context
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search)
      const data = params.get('data')
      if (data && VALID_SCENARIOS.includes(data as BreakUIScenario)) {
        return data as BreakUIScenario
      }
    }
  }

  return null
}

