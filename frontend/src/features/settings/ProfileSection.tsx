import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm, useWatch } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

import { FormField } from '@/components/common/FormField'
import { Spinner } from '@/components/common/states'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { FormAlert } from '@/features/auth/AuthCard'
import { useAuth } from '@/features/auth/AuthProvider'
import { applyServerErrors } from '@/lib/forms'
import { api } from '@/services/api/client'
import type { UserOut } from '@/services/api/types'

const schema = z.object({
  full_name: z.string().trim().min(1, 'Enter your name').max(120),
  email: z.string().trim().email('Enter a valid email address'),
  current_password: z.string().max(128),
})
type Values = z.infer<typeof schema>

export function ProfileSection() {
  const { user, setUser } = useAuth()
  const [formError, setFormError] = useState<string | null>(null)
  const { register, handleSubmit, setError, formState, control, resetField } = useForm<Values>({
    resolver: zodResolver(schema),
    values: { full_name: user?.full_name ?? '', email: user?.email ?? '', current_password: '' },
  })
  const emailChanged = (useWatch({ control, name: 'email' }) ?? '').trim().toLowerCase() !== (user?.email ?? '').toLowerCase()

  const onSubmit = handleSubmit(async (v) => {
    setFormError(null)
    const body: Record<string, string> = { full_name: v.full_name }
    if (emailChanged) {
      body.email = v.email
      if (v.current_password) body.current_password = v.current_password
    }
    try {
      const updated = await api.patch<UserOut>('/users/me', body)
      setUser(updated)
      resetField('current_password')
      toast.success('Profile updated')
    } catch (err) {
      setFormError(applyServerErrors(err, setError, ['full_name', 'email', 'current_password']))
    }
  })

  return (
    <form onSubmit={onSubmit} noValidate className="grid max-w-md gap-4">
      <FormAlert message={formError} />
      <FormField label="Full name" error={formState.errors.full_name?.message}>
        {(p) => <Input autoComplete="name" {...p} {...register('full_name')} />}
      </FormField>
      <FormField label="Email" error={formState.errors.email?.message}>
        {(p) => <Input type="email" autoComplete="email" {...p} {...register('email')} />}
      </FormField>
      {emailChanged && (
        <FormField label="Current password" hint="Required to change your email." error={formState.errors.current_password?.message}>
          {(p) => <Input type="password" autoComplete="current-password" {...p} {...register('current_password')} />}
        </FormField>
      )}
      <div>
        <Button type="submit" disabled={formState.isSubmitting}>
          {formState.isSubmitting && <Spinner />} Save profile
        </Button>
      </div>
    </form>
  )
}
