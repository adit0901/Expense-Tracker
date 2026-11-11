import { PeriodFilter } from '@/components/common/PeriodFilter'
import { PageHeader } from '@/components/common/states'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { usePeriodParam } from '@/lib/period'

import { ExpenseReportView, IncomeReportView, SavingsTrendView } from './views'

export function ReportsPage() {
  const { query, ready } = usePeriodParam('this_year')
  return (
    <div>
      <PageHeader title="Reports & Analytics" description="Income, expenses and savings over time. Export any view as CSV."
        actions={<PeriodFilter defaultKind="this_year" />} />
      <Tabs defaultValue="income">
        <TabsList>
          <TabsTrigger value="income">Income</TabsTrigger>
          <TabsTrigger value="expenses">Expenses</TabsTrigger>
          <TabsTrigger value="savings">Savings rate</TabsTrigger>
        </TabsList>
        <TabsContent value="income" className="mt-4"><IncomeReportView query={query} enabled={ready} /></TabsContent>
        <TabsContent value="expenses" className="mt-4"><ExpenseReportView query={query} enabled={ready} /></TabsContent>
        <TabsContent value="savings" className="mt-4"><SavingsTrendView query={query} enabled={ready} /></TabsContent>
      </Tabs>
    </div>
  )
}
