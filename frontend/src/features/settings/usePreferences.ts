import { useQuery } from '@tanstack/react-query'
import { useEffect } from 'react'

import { useTheme } from '@/app/theme'
import { useAuth } from '@/features/auth/AuthProvider'
import type { DateFormat, NumberGrouping } from '@/lib/format'
import { formatDate, formatMoney } from '@/lib/format'
import { api } from '@/services/api/client'
import type { PreferencesOut } from '@/services/api/types'

export const preferencesKey = ['preferences'] as const

const DEFAULTS: PreferencesOut = {
  currency: 'INR',
  theme: 'system',
  locale: 'en-IN',
  date_format: 'DD/MM/YYYY',
  number_grouping: 'indian',
  week_start: 'monday',
  timezone: 'Asia/Kolkata',
}

export function usePreferences(): PreferencesOut {
  const { status } = useAuth()
  const { data } = useQuery({
    queryKey: preferencesKey,
    queryFn: () => api.get<PreferencesOut>('/users/me/preferences'),
    enabled: status === 'authenticated',
    staleTime: 5 * 60_000,
  })
  return data ?? DEFAULTS
}

/** Applies the server-stored theme preference once it loads. */
export function useSyncThemeFromPreferences(): void {
  const { status } = useAuth()
  const { theme, setTheme } = useTheme()
  const { data } = useQuery({
    queryKey: preferencesKey,
    queryFn: () => api.get<PreferencesOut>('/users/me/preferences'),
    enabled: status === 'authenticated',
    staleTime: 5 * 60_000,
  })
  useEffect(() => {
    if (data && data.theme !== theme) setTheme(data.theme)
    // only react to server value changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data?.theme])
}

/** Formatters bound to the user's preferences. */
export function useFormatters() {
  const prefs = usePreferences()
  const grouping = prefs.number_grouping as NumberGrouping
  const dateFormat = prefs.date_format as DateFormat
  return {
    money: (v: string | null | undefined) => formatMoney(v, { grouping, currency: prefs.currency }),
    date: (v: string | null | undefined) => formatDate(v, dateFormat),
    prefs,
  }
}
