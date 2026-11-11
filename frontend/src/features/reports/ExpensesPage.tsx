import { PeriodFilter } from '@/components/common/PeriodFilter'
import { PageHeader } from '@/components/common/states'
import { usePeriodParam } from '@/lib/period'

import { ExpenseReportView } from './views'

export function ExpensesPage() {
  const { query, ready } = usePeriodParam('this_month')
  return (
    <div>
      <PageHeader title="Expenses" description="Where your money went, by category and payment method."
        actions={<PeriodFilter />} />
      <ExpenseReportView query={query} enabled={ready} />
    </div>
  )
}
