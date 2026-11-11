import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export function AuthCard({ title, description, children, footer }: {
  title: string
  description?: string
  children: React.ReactNode
  footer?: React.ReactNode
}) {
  return (
    <main className="flex min-h-svh items-center justify-center bg-muted/40 p-4">
      <div className="w-full max-w-sm">
        <p className="mb-4 text-center text-xl font-semibold">FinTrack</p>
        <Card>
          <CardHeader>
            <CardTitle>
              <h1 className="text-lg">{title}</h1>
            </CardTitle>
            {description && <CardDescription>{description}</CardDescription>}
          </CardHeader>
          <CardContent>{children}</CardContent>
        </Card>
        {footer && <div className="mt-4 text-center text-sm text-muted-foreground">{footer}</div>}
      </div>
    </main>
  )
}

export function FormAlert({ message, tone = 'error' }: { message: string | null; tone?: 'error' | 'success' }) {
  if (!message) return null
  return (
    <p
      role={tone === 'error' ? 'alert' : 'status'}
      className={
        tone === 'error'
          ? 'rounded-md border border-destructive/40 bg-destructive/10 p-2 text-sm text-destructive'
          : 'rounded-md border border-success/40 bg-success/10 p-2 text-sm'
      }
    >
      {message}
    </p>
  )
}
