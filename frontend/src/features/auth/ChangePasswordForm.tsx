import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import type { z } from 'zod'

import { FormField } from '@/components/common/FormField'
import { Spinner } from '@/components/common/states'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { applyServerErrors } from '@/lib/forms'
import { api } from '@/services/api/client'

import { FormAlert } from './AuthCard'
import { changePasswordSchema } from './schemas'

type Values = z.infer<typeof changePasswordSchema>

export function ChangePasswordForm() {
  const [formError, setFormError] = useState<string | null>(null)
  const { register, handleSubmit, setError, formState, reset } = useForm<Values>({
    resolver: zodResolver(changePasswordSchema),
    defaultValues: { current_password: '', new_password: '', confirm_password: '' },
  })
  const onSubmit = handleSubmit(async ({ current_password, new_password }) => {
    setFormError(null)
    try {
      await api.post('/auth/password/change', { current_password, new_password })
      reset()
      toast.success('Password changed. Other sessions were signed out.')
    } catch (err) {
      setFormError(applyServerErrors(err, setError, ['current_password', 'new_password']))
    }
  })
  return (
    <form onSubmit={onSubmit} noValidate className="grid max-w-md gap-4">
      <FormAlert message={formError} />
      <FormField label="Current password" error={formState.errors.current_password?.message}>
        {(p) => <Input type="password" autoComplete="current-password" {...p} {...register('current_password')} />}
      </FormField>
      <FormField label="New password" error={formState.errors.new_password?.message}>
        {(p) => <Input type="password" autoComplete="new-password" {...p} {...register('new_password')} />}
      </FormField>
      <FormField label="Confirm new password" error={formState.errors.confirm_password?.message}>
        {(p) => <Input type="password" autoComplete="new-password" {...p} {...register('confirm_password')} />}
      </FormField>
      <div>
        <Button type="submit" disabled={formState.isSubmitting}>
          {formState.isSubmitting && <Spinner />} Change password
        </Button>
      </div>
    </form>
  )
}
