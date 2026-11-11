import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Download, Paperclip, Trash2 } from 'lucide-react'
import { useId, useState } from 'react'
import { toast } from 'sonner'

import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import { Spinner, errorMessage } from '@/components/common/states'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { qk } from '@/lib/queryKeys'
import { ApiError, api, download } from '@/services/api/client'
import type { AttachmentOut, TransactionOut } from '@/services/api/types'

export const MAX_RECEIPT_BYTES = 10 * 1024 * 1024
export const MAX_RECEIPTS = 5
const ACCEPT = 'application/pdf,image/jpeg,image/png,image/webp'

export function uploadErrorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 413) return 'That file is larger than 10 MB.'
    if (err.code === 'unsupported_file_type') return 'Only PDF, JPEG, PNG or WebP receipts can be uploaded.'
    if (err.code === 'attachment_limit') return `A transaction can have at most ${MAX_RECEIPTS} receipts.`
  }
  return errorMessage(err)
}

function sizeLabel(bytes: number): string {
  return bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`
}

export function Receipts({ transaction }: { transaction: TransactionOut }) {
  const qc = useQueryClient()
  const inputId = useId()
  const [error, setError] = useState<string | null>(null)
  const [deleting, setDeleting] = useState<AttachmentOut | null>(null)
  const atLimit = transaction.attachments.length >= MAX_RECEIPTS

  const upload = useMutation({
    mutationFn: (file: File) => {
      const fd = new FormData()
      fd.append('file', file)
      return api.post<AttachmentOut>(`/transactions/${transaction.id}/attachments`, fd)
    },
    onSuccess: async () => {
      setError(null)
      await qc.invalidateQueries({ queryKey: qk.transactions })
      toast.success('Receipt attached')
    },
    onError: (err) => setError(uploadErrorMessage(err)),
  })
  const remove = useMutation({
    mutationFn: (a: AttachmentOut) => api.del(`/attachments/${a.id}`),
    onSuccess: async () => {
      setDeleting(null)
      await qc.invalidateQueries({ queryKey: qk.transactions })
      toast.success('Receipt deleted')
    },
    onError: (err) => toast.error(errorMessage(err)),
  })

  const onFile = (file: File | undefined) => {
    if (!file) return
    if (file.size > MAX_RECEIPT_BYTES) {
      setError('That file is larger than 10 MB.')
      return
    }
    upload.mutate(file)
  }

  return (
    <section aria-label="Receipts" className="grid gap-2">
      <h3 className="text-sm font-medium">Receipts</h3>
      {transaction.attachments.length === 0 && <p className="text-sm text-muted-foreground">No receipts attached.</p>}
      <ul className="grid gap-1">
        {transaction.attachments.map((a) => (
          <li key={a.id} className="flex items-center gap-2 text-sm">
            <Paperclip className="size-4 shrink-0" aria-hidden />
            <span className="min-w-0 flex-1 truncate">{a.original_name}</span>
            <span className="text-xs text-muted-foreground">{sizeLabel(a.size_bytes)}</span>
            <Button variant="ghost" size="icon-sm" aria-label={`Download ${a.original_name}`}
              onClick={() => void download(`/attachments/${a.id}`, undefined, a.original_name).catch((e) => toast.error(errorMessage(e)))}>
              <Download aria-hidden />
            </Button>
            <Button variant="ghost" size="icon-sm" aria-label={`Delete ${a.original_name}`} onClick={() => setDeleting(a)}>
              <Trash2 aria-hidden />
            </Button>
          </li>
        ))}
      </ul>
      <div className="flex items-center gap-2">
        <Label htmlFor={inputId} className="sr-only">Attach a receipt</Label>
        <input id={inputId} type="file" accept={ACCEPT} disabled={atLimit || upload.isPending}
          className="text-sm file:mr-2 file:rounded-md file:border file:bg-secondary file:px-2 file:py-1"
          onChange={(e) => {
            onFile(e.target.files?.[0])
            e.target.value = ''
          }} />
        {upload.isPending && <Spinner />}
      </div>
      <p className="text-xs text-muted-foreground">PDF, JPEG, PNG or WebP, up to 10 MB, max {MAX_RECEIPTS} per transaction.</p>
      {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
      <ConfirmDialog open={!!deleting} onOpenChange={(o) => !o && setDeleting(null)}
        title="Delete receipt?" description={deleting?.original_name} pending={remove.isPending}
        onConfirm={() => deleting && remove.mutate(deleting)} />
    </section>
  )
}
