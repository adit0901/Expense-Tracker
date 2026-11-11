import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate, useSearchParams } from 'react-router'
import { toast } from 'sonner'
import type { z } from 'zod'

import { FormField } from '@/components/common/FormField'
import { Spinner } from '@/components/common/states'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { applyServerErrors } from '@/lib/forms'
import { api } from '@/services/api/client'

import { AuthCard, FormAlert } from './AuthCard'
import { resetSchema } from './schemas'

type Values = z.infer<typeof resetSchema>

export function ResetPasswordPage() {
  const [params] = useSearchParams()
  const token = params.get('token') ?? ''
  const navigate = useNavigate()
  const [formError, setFormError] = useState<string | null>(token ? null : 'This reset link is missing its token.')
  const { register, handleSubmit, setError, formState } = useForm<Values>({
    resolver: zodResolver(resetSchema),
    defaultValues: { new_password: '', confirm_password: '' },
  })
  const onSubmit = handleSubmit(async ({ new_password }) => {
    setFormError(null)
    try {
      await api.post('/auth/password-reset/confirm', { token, new_password }, { anonymous: true })
      toast.success('Password updated. Please sign in.')
      navigate('/login', { replace: true })
    } catch (err) {
      setFormError(applyServerErrors(err, setError, ['new_password']))
    }
  })
  return (
    <AuthCard
      title="Choose a new password"
      footer={<Link className="text-primary underline underline-offset-4" to="/forgot-password">Request a new link</Link>}
    >
      <form onSubmit={onSubmit} noValidate className="grid gap-4">
        <FormAlert message={formError} />
        <FormField label="New password" hint="At least 10 characters." error={formState.errors.new_password?.message}>
          {(p) => <Input type="password" autoComplete="new-password" {...p} {...register('new_password')} />}
        </FormField>
        <FormField label="Confirm new password" error={formState.errors.confirm_password?.message}>
          {(p) => <Input type="password" autoComplete="new-password" {...p} {...register('confirm_password')} />}
        </FormField>
        <Button type="submit" disabled={formState.isSubmitting || !token}>
          {formState.isSubmitting && <Spinner />} Update password
        </Button>
      </form>
    </AuthCard>
  )
}
