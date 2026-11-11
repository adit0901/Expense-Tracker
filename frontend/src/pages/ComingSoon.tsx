import { Clock } from 'lucide-react'

import { PageHeader } from '@/components/common/states'

/** Placeholder for unreleased sections. Deliberately makes no API calls. */
export function ComingSoon({ title, release }: { title: string; release?: string }) {
  return (
    <div>
      <PageHeader title={title} />
      <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed p-10 text-center">
        <Clock className="size-8 text-muted-foreground" aria-hidden />
        <p className="text-lg font-medium">Coming in a later release</p>
        <p className="max-w-md text-sm text-muted-foreground">
          {title} is planned for FinTrack {release ?? 'a future release'}. Keep tracking your income and
          expenses in the meantime.
        </p>
      </div>
    </div>
  )
}
