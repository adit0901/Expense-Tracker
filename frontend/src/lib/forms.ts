import type { FieldValues, Path, UseFormSetError } from 'react-hook-form'

import { ApiError } from '@/services/api/client'

/**
 * Map a server error onto form fields (keeps the user's input). Returns the message to show
 * at form level when it isn't tied to a known field.
 */
export function applyServerErrors<T extends FieldValues>(
  err: unknown,
  setError: UseFormSetError<T>,
  fields: readonly string[],
  aliases: Record<string, string> = {},
): string | null {
  if (!(err instanceof ApiError)) return err instanceof Error ? err.message : 'Something went wrong'
  let mapped = false
  for (const d of err.details) {
    const raw = typeof d.field === 'string' ? d.field.split('.')[0] ?? '' : ''
    const field = aliases[raw] ?? raw
    if (field && fields.includes(field)) {
      const msg = typeof d.message === 'string' && d.message.length > 20 ? d.message : err.message
      setError(field as Path<T>, { type: 'server', message: msg })
      mapped = true
    }
  }
  return mapped && err.status === 422 ? null : err.message
}
