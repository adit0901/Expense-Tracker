import { useState } from 'react'

import { LoadingBlock } from '@/components/common/states'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useFormatters } from '@/features/settings/usePreferences'
import type { InstallmentOut, LoanOut } from '@/services/api/types'

import { useLoanSchedule } from './api'
import { ConfirmPaymentDialog } from './ConfirmPaymentDialog'

interface LoanScheduleModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  loan: LoanOut
}

export function LoanScheduleModal({ open, onOpenChange, loan }: LoanScheduleModalProps) {
  const { money, date } = useFormatters()
  const scheduleQuery = useLoanSchedule(loan.id)

  const [paymentInstallment, setPaymentInstallment] = useState<InstallmentOut | null>(null)

  const schedule = scheduleQuery.data
  const installments = schedule?.installments ?? []

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-4xl">
          <DialogHeader>
            <div className="flex items-center justify-between">
              <DialogTitle>Amortization Schedule: {loan.lender}</DialogTitle>
              <div className="flex items-center gap-2 text-xs">
                <span className="text-muted-foreground">Total Interest:</span>
                <strong className="text-destructive tabular-nums">
                  {schedule ? money(String(schedule.total_interest)) : '—'}
                </strong>
              </div>
            </div>
            <DialogDescription>
              Complete reducing-balance repayment schedule with principal & interest breakdowns.
            </DialogDescription>
          </DialogHeader>

          <div className="py-2">
            {scheduleQuery.isPending ? (
              <LoadingBlock label="Loading schedule..." />
            ) : installments.length === 0 ? (
              <div className="py-8 text-center text-sm text-muted-foreground">
                No schedule available for this loan.
              </div>
            ) : (
              <div className="max-h-[60vh] overflow-y-auto rounded-md border">
                <Table>
                  <TableHeader className="sticky top-0 bg-background z-10 shadow-xs">
                    <TableRow>
                      <TableHead className="w-14">#</TableHead>
                      <TableHead>Due Date</TableHead>
                      <TableHead className="text-right">Payment</TableHead>
                      <TableHead className="text-right">Principal</TableHead>
                      <TableHead className="text-right">Interest</TableHead>
                      <TableHead className="text-right">Closing Balance</TableHead>
                      <TableHead className="text-center">Status</TableHead>
                      <TableHead className="w-20"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {installments.map((inst) => (
                      <TableRow key={inst.installment_no}>
                        <TableCell className="font-medium text-xs text-muted-foreground">
                          {inst.installment_no}
                        </TableCell>
                        <TableCell className="text-xs">{date(String(inst.due_date))}</TableCell>
                        <TableCell className="text-right font-medium tabular-nums">
                          {money(String(inst.payment))}
                        </TableCell>
                        <TableCell className="text-right text-xs tabular-nums text-foreground">
                          {money(String(inst.principal))}
                        </TableCell>
                        <TableCell className="text-right text-xs tabular-nums text-destructive">
                          {money(String(inst.interest))}
                        </TableCell>
                        <TableCell className="text-right text-xs tabular-nums">
                          {money(String(inst.closing_outstanding))}
                        </TableCell>
                        <TableCell className="text-center">
                          {inst.is_paid ? (
                            <Badge variant="outline" className="border-emerald-500 text-emerald-500 text-[10px]">
                              Paid
                            </Badge>
                          ) : (
                            <Badge variant="outline" className="text-[10px]">
                              Due
                            </Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          {!inst.is_paid && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-7 text-xs"
                              onClick={() => setPaymentInstallment(inst)}
                            >
                              Pay
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {paymentInstallment && (
        <ConfirmPaymentDialog
          open={Boolean(paymentInstallment)}
          onOpenChange={(op) => !op && setPaymentInstallment(null)}
          loan={loan}
          installment={paymentInstallment}
        />
      )}
    </>
  )
}

