import { useState } from 'react'
import { toast } from 'sonner'

import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import { FormField } from '@/components/common/FormField'
import { errorMessage } from '@/components/common/states'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useAuth } from '@/features/auth/AuthProvider'
import { api } from '@/services/api/client'

export function DeleteAccountSection() {
  const { endSession, user } = useAuth()
  const [open, setOpen] = useState(false)
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)

  const onConfirm = async () => {
    setPending(true)
    setError(null)
    try {
      await api.del('/users/me', undefined, { password })
      endSession('/login')
      toast.success('Your account and all its data were deleted')
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="max-w-md space-y-3">
      <p className="text-sm text-muted-foreground">
        Permanently delete your FinTrack account, all accounts, categories, transactions and uploaded
        receipts. This cannot be undone.
      </p>
      <Button variant="destructive" onClick={() => setOpen(true)}>
        Delete my account
      </Button>
      <ConfirmDialog
        open={open}
        onOpenChange={(o) => {
          setOpen(o)
          if (!o) {
            setPassword('')
            setError(null)
          }
        }}
        title="Delete your account?"
        description={<>This permanently deletes <strong>{user?.email}</strong> and all of its financial data and receipts.</>}
        confirmLabel="Delete account permanently"
        onConfirm={() => void onConfirm()}
        pending={pending || !password}
      >
        <FormField label="Enter your password to confirm" error={error ?? undefined}>
          {(p) => (
            <Input type="password" autoComplete="current-password" value={password}
              onChange={(e) => setPassword(e.target.value)} {...p} />
          )}
        </FormField>
      </ConfirmDialog>
    </div>
  )
}
