import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

import { useTheme } from '@/app/theme'
import { errorMessage } from '@/components/common/states'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { formatMoney } from '@/lib/format'
import { api } from '@/services/api/client'
import type { PreferencesOut, PreferencesUpdate } from '@/services/api/types'

import { preferencesKey, usePreferences } from './usePreferences'

const TIMEZONES = ['Asia/Kolkata', 'Asia/Dubai', 'Asia/Singapore', 'Europe/London', 'America/New_York', 'UTC']

function PrefSelect({ label, value, options, onChange }: {
  label: string
  value: string
  options: { value: string; label: string }[]
  onChange: (v: string) => void
}) {
  const id = `pref-${label.toLowerCase().replace(/\W+/g, '-')}`
  return (
    <div className="grid gap-1.5">
      <Label htmlFor={id}>{label}</Label>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger id={id} className="w-full">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {options.map((o) => (
            <SelectItem key={o.value} value={o.value}>
              {o.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}

export function PreferencesSection() {
  const prefs = usePreferences()
  const { setTheme } = useTheme()
  const qc = useQueryClient()
  const mutation = useMutation({
    mutationFn: (body: PreferencesUpdate) => api.patch<PreferencesOut>('/users/me/preferences', body),
    onSuccess: (data) => {
      qc.setQueryData(preferencesKey, data)
      setTheme(data.theme)
      toast.success('Preferences saved')
    },
    onError: (err) => toast.error(errorMessage(err)),
  })
  const save = (body: PreferencesUpdate) => mutation.mutate(body)
  const sample = '1234567.89'

  return (
    <div className="grid max-w-md gap-4">
      <div className="grid gap-1.5">
        <Label>Reporting currency</Label>
        <p className="text-sm">INR (Indian Rupee)</p>
        <p className="text-xs text-muted-foreground">Other reporting currencies are not supported yet.</p>
      </div>
      <PrefSelect
        label="Theme"
        value={prefs.theme}
        onChange={(v) => save({ theme: v as PreferencesOut['theme'] })}
        options={[
          { value: 'system', label: 'System' },
          { value: 'light', label: 'Light' },
          { value: 'dark', label: 'Dark' },
        ]}
      />
      <PrefSelect
        label="Number grouping"
        value={prefs.number_grouping}
        onChange={(v) => save({ number_grouping: v as PreferencesOut['number_grouping'] })}
        options={[
          { value: 'indian', label: `Indian (lakh/crore) — ${formatMoney(sample, { grouping: 'indian' })}` },
          { value: 'international', label: `International — ${formatMoney(sample, { grouping: 'international' })}` },
        ]}
      />
      <PrefSelect
        label="Date format"
        value={prefs.date_format}
        onChange={(v) => save({ date_format: v as PreferencesOut['date_format'] })}
        options={[
          { value: 'DD/MM/YYYY', label: 'DD/MM/YYYY' },
          { value: 'MM/DD/YYYY', label: 'MM/DD/YYYY' },
          { value: 'YYYY-MM-DD', label: 'YYYY-MM-DD' },
        ]}
      />
      <PrefSelect
        label="Week starts on"
        value={prefs.week_start}
        onChange={(v) => save({ week_start: v as PreferencesOut['week_start'] })}
        options={[
          { value: 'monday', label: 'Monday' },
          { value: 'sunday', label: 'Sunday' },
        ]}
      />
      <PrefSelect
        label="Time zone"
        value={prefs.timezone}
        onChange={(v) => save({ timezone: v })}
        options={TIMEZONES.map((t) => ({ value: t, label: t }))}
      />
    </div>
  )
}
