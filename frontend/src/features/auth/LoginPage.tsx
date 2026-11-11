import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router'
import type { z } from 'zod'

import { FormField } from '@/components/common/FormField'
import { Spinner } from '@/components/common/states'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { applyServerErrors } from '@/lib/forms'

import { AuthCard, FormAlert } from './AuthCard'
import { useAuth } from './AuthProvider'
import { loginSchema } from './schemas'

type Values = z.infer<typeof loginSchema>

export function safeNext(next: string | null): string {
  return next && next.startsWith('/') && !next.startsWith('//') ? next : '/'
}

export function LoginPage() {
  const { login, status } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const next = safeNext(params.get('next'))
  const [formError, setFormError] = useState<string | null>(null)
  const { register, handleSubmit, setError, formState } = useForm<Values>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', password: '' },
  })

  if (status === 'authenticated') return <Navigate to={next} replace />

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null)
    try {
      await login(values.email, values.password)
      navigate(next, { replace: true })
    } catch (err) {
      setFormError(applyServerErrors(err, setError, ['email', 'password']))
    }
  })

  return (
    <AuthCard
      title="Sign in"
      description="Welcome back. Sign in to see your finances."
      footer={
        <>
          New to FinTrack? <Link className="text-primary underline underline-offset-4" to="/register">Create an account</Link>
        </>
      }
    >
      <form onSubmit={onSubmit} noValidate className="grid gap-4">
        <FormAlert message={formError} />
        <FormField label="Email" error={formState.errors.email?.message}>
          {(p) => <Input type="email" autoComplete="email" {...p} {...register('email')} />}
        </FormField>
        <FormField label="Password" error={formState.errors.password?.message}>
          {(p) => <Input type="password" autoComplete="current-password" {...p} {...register('password')} />}
        </FormField>
        <Button type="submit" disabled={formState.isSubmitting}>
          {formState.isSubmitting && <Spinner />} Sign in
        </Button>
        <Link to="/forgot-password" className="text-center text-sm text-primary underline underline-offset-4">
          Forgot your password?
        </Link>
      </form>
    </AuthCard>
  )
}
