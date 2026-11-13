import { createPortal } from 'react-dom'
import { useSearchParams } from 'react-router'
import { cn } from '@/lib/utils'
import type { BreakUIScenario } from './test-scenarios'

interface ScenarioOption {
  key: BreakUIScenario | 'live'
  label: string
}

const OPTIONS: ScenarioOption[] = [
  { key: 'demo', label: 'Demo' },
  { key: 'worst', label: 'Worst case' },
  { key: 'empty', label: 'Empty' },
  { key: 'one', label: 'One' },
  { key: 'huge', label: '1,000 rows' },
  { key: 'live', label: 'Live API' },
]

export function BreakUISelector() {
  if (!import.meta.env.DEV) {
    return null
  }

  const [searchParams, setSearchParams] = useSearchParams()
  const currentScenario = (searchParams.get('data') as BreakUIScenario) || 'live'

  const handleSelect = (key: BreakUIScenario | 'live') => {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        if (key === 'live') {
          next.delete('data')
        } else {
          next.set('data', key)
        }
        return next
      },
      { replace: true },
    )
  }

  const content = (
    <aside
      aria-label="Break UI scenario selector"
      onPointerDown={(e) => e.stopPropagation()}
      className="fixed bottom-4 left-1/2 -translate-x-1/2 z-[100] pointer-events-auto"
    >
      <div className="flex items-center gap-1 rounded-full border border-border/80 bg-background/95 p-1 shadow-2xl backdrop-blur-md">
        <span className="px-2.5 py-0.5 text-[10px] font-semibold tracking-wider text-muted-foreground uppercase select-none">
          Break UI
        </span>
        <div className="flex items-center gap-0.5 rounded-full bg-muted/60 p-0.5">
          {OPTIONS.map((opt) => {
            const isActive = currentScenario === opt.key
            return (
              <button
                key={opt.key}
                type="button"
                onClick={() => handleSelect(opt.key)}
                className={cn(
                  'rounded-full px-2.5 py-1 text-xs font-medium transition-colors select-none',
                  isActive
                    ? 'bg-foreground text-background shadow-xs font-semibold'
                    : 'text-muted-foreground hover:text-foreground hover:bg-background/80',
                )}
                aria-pressed={isActive}
              >
                {opt.label}
              </button>
            )
          })}
        </div>
      </div>
    </aside>
  )

  if (typeof document === 'undefined') {
    return null
  }

  return createPortal(content, document.body)
}
