import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import { errorMessage } from '@/components/common/states'
import { useFormatters } from '@/features/settings/usePreferences'
import { TRANSACTION_TYPE_LABELS } from '@/lib/format'
import { invalidateFinancials } from '@/lib/queryKeys'
import { api } from '@/services/api/client'
import type { TransactionOut } from '@/services/api/types'

export function DeleteTransactionDialog({ transaction, onClose }: { transaction: TransactionOut | null; onClose: () => void }) {
  const qc = useQueryClient()
  const { money, date } = useFormatters()
  const remove = useMutation({
    mutationFn: (t: TransactionOut) => api.del(`/transactions/${t.id}`),
    onSuccess: async () => {
      await invalidateFinancials(qc)
      toast.success('Transaction deleted')
      onClose()
    },
    onError: (err) => toast.error(errorMessage(err)),
  })
  const t = transaction
  return (
    <ConfirmDialog
      open={!!t}
      onOpenChange={(o) => !o && onClose()}
      title="Delete this transaction?"
      description={t && (
        <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
          <dt className="text-muted-foreground">Date</dt><dd>{date(t.txn_date)}</dd>
          <dt className="text-muted-foreground">Amount</dt><dd>{money(t.amount)} ({TRANSACTION_TYPE_LABELS[t.type]})</dd>
          <dt className="text-muted-foreground">Description</dt><dd>{t.description ?? t.payee ?? '—'}</dd>
          {t.attachments.length > 0 && (<><dt className="text-muted-foreground">Receipts</dt><dd>{t.attachments.length} will be deleted</dd></>)}
        </dl>
      )}
      pending={remove.isPending}
      onConfirm={() => t && remove.mutate(t)}
    />
  )
}
