import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, Navigate, useNavigate } from 'react-router'
import { toast } from 'sonner'
import type { z } from 'zod'

import { FormField } from '@/components/common/FormField'
import { Spinner } from '@/components/common/states'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { applyServerErrors } from '@/lib/forms'
import { api } from '@/services/api/client'
import type { UserOut } from '@/services/api/types'

import { AuthCard, FormAlert } from './AuthCard'
import { useAuth } from './AuthProvider'
import { registerSchema } from './schemas'

type Values = z.infer<typeof registerSchema>

export function RegisterPage() {
  const { login, status } = useAuth()
  const navigate = useNavigate()
  const [formError, setFormError] = useState<string | null>(null)
  const { register, handleSubmit, setError, formState } = useForm<Values>({
    resolver: zodResolver(registerSchema),
    defaultValues: { full_name: '', email: '', password: '', confirm_password: '' },
  })

  if (status === 'authenticated') return <Navigate to="/" replace />

  const onSubmit = handleSubmit(async ({ full_name, email, password }) => {
    setFormError(null)
    try {
      await api.post<UserOut>('/auth/register', { full_name, email, password }, { anonymous: true })
    } catch (err) {
      setFormError(applyServerErrors(err, setError, ['full_name', 'email', 'password']))
      return
    }
    await login(email, password)
    toast.success('Welcome to FinTrack')
    navigate('/', { replace: true })
  })

  return (
    <AuthCard
      title="Create your account"
      description="Track income, expenses and savings in one place."
      footer={
        <>
          Already have an account? <Link className="text-primary underline underline-offset-4" to="/login">Sign in</Link>
        </>
      }
    >
      <form onSubmit={onSubmit} noValidate className="grid gap-4">
        <FormAlert message={formError} />
        <FormField label="Full name" error={formState.errors.full_name?.message}>
          {(p) => <Input autoComplete="name" {...p} {...register('full_name')} />}
        </FormField>
        <FormField label="Email" error={formState.errors.email?.message}>
          {(p) => <Input type="email" autoComplete="email" {...p} {...register('email')} />}
        </FormField>
        <FormField label="Password" hint="At least 10 characters; avoid common passwords." error={formState.errors.password?.message}>
          {(p) => <Input type="password" autoComplete="new-password" {...p} {...register('password')} />}
        </FormField>
        <FormField label="Confirm password" error={formState.errors.confirm_password?.message}>
          {(p) => <Input type="password" autoComplete="new-password" {...p} {...register('confirm_password')} />}
        </FormField>
        <Button type="submit" disabled={formState.isSubmitting}>
          {formState.isSubmitting && <Spinner />} Create account
        </Button>
      </form>
    </AuthCard>
  )
}
