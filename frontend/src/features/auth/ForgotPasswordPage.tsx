import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link } from 'react-router'
import type { z } from 'zod'

import { FormField } from '@/components/common/FormField'
import { Spinner, errorMessage } from '@/components/common/states'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { api } from '@/services/api/client'

import { AuthCard, FormAlert } from './AuthCard'
import { forgotSchema } from './schemas'

type Values = z.infer<typeof forgotSchema>

export function ForgotPasswordPage() {
  const [sent, setSent] = useState<string | null>(null)
  const [formError, setFormError] = useState<string | null>(null)
  const { register, handleSubmit, formState } = useForm<Values>({
    resolver: zodResolver(forgotSchema),
    defaultValues: { email: '' },
  })
  const onSubmit = handleSubmit(async (values) => {
    setFormError(null)
    try {
      const res = await api.post<{ message: string }>('/auth/password-reset/request', values, { anonymous: true })
      setSent(res.message)
    } catch (err) {
      setFormError(errorMessage(err))
    }
  })
  return (
    <AuthCard
      title="Reset your password"
      description="We'll email you a link that's valid for 30 minutes."
      footer={<Link className="text-primary underline underline-offset-4" to="/login">Back to sign in</Link>}
    >
      <form onSubmit={onSubmit} noValidate className="grid gap-4">
        <FormAlert message={formError} />
        <FormAlert message={sent} tone="success" />
        <FormField label="Email" error={formState.errors.email?.message}>
          {(p) => <Input type="email" autoComplete="email" {...p} {...register('email')} />}
        </FormField>
        <Button type="submit" disabled={formState.isSubmitting}>
          {formState.isSubmitting && <Spinner />} Send reset link
        </Button>
      </form>
    </AuthCard>
  )
}
