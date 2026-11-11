import { z } from 'zod'

// Mirrors server rules; the server stays authoritative (e.g. common-password list).
export const passwordSchema = z.string().min(10, 'Password must be at least 10 characters').max(128)

export const loginSchema = z.object({
  email: z.string().trim().email('Enter a valid email address'),
  password: z.string().min(1, 'Enter your password'),
})

export const registerSchema = z
  .object({
    full_name: z.string().trim().min(1, 'Enter your name').max(120),
    email: z.string().trim().email('Enter a valid email address'),
    password: passwordSchema,
    confirm_password: z.string(),
  })
  .refine((v) => v.password === v.confirm_password, {
    path: ['confirm_password'],
    message: 'Passwords do not match',
  })

export const forgotSchema = z.object({ email: z.string().trim().email('Enter a valid email address') })

export const resetSchema = z
  .object({ new_password: passwordSchema, confirm_password: z.string() })
  .refine((v) => v.new_password === v.confirm_password, {
    path: ['confirm_password'],
    message: 'Passwords do not match',
  })

export const changePasswordSchema = z
  .object({
    current_password: z.string().min(1, 'Enter your current password'),
    new_password: passwordSchema,
    confirm_password: z.string(),
  })
  .refine((v) => v.new_password === v.confirm_password, {
    path: ['confirm_password'],
    message: 'Passwords do not match',
  })
