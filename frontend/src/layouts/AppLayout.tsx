import { LogOut, Menu, Moon, Sun } from 'lucide-react'
import { useState } from 'react'
import { NavLink, Navigate, Outlet, useLocation } from 'react-router'

import { NAVIGATION, type NavItem } from '@/app/navigation'
import { useTheme } from '@/app/theme'
import { Spinner } from '@/components/common/states'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { loginPath, useAuth } from '@/features/auth/AuthProvider'
import { useSyncThemeFromPreferences } from '@/features/settings/usePreferences'
import { cn } from '@/lib/utils'

function NavEntry({ item, onNavigate, depth = 0 }: { item: NavItem; onNavigate?: () => void; depth?: number }) {
  const Icon = item.icon
  return (
    <li>
      <NavLink
        to={item.to}
        end={item.to === '/'}
        onClick={onNavigate}
        className={({ isActive }) =>
          cn(
            'flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors outline-none',
            'focus-visible:ring-2 focus-visible:ring-ring',
            depth > 0 && 'ml-6 py-1.5',
            isActive
              ? 'bg-sidebar-accent font-medium text-sidebar-accent-foreground'
              : 'text-sidebar-foreground hover:bg-sidebar-accent/60',
          )
        }
      >
        {Icon && <Icon className="size-4 shrink-0" aria-hidden />}
        <span className="truncate">{item.label}</span>
        {item.release && depth === 0 && (
          <Badge variant="outline" className="ml-auto text-[10px]">
            Soon
          </Badge>
        )}
      </NavLink>
      {item.children && (
        <ul className="mt-0.5 space-y-0.5">
          {item.children.map((child) => (
            <NavEntry key={child.to} item={child} onNavigate={onNavigate} depth={depth + 1} />
          ))}
        </ul>
      )}
    </li>
  )
}

function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <nav aria-label="Main navigation" className="flex h-full flex-col gap-2">
      <ul className="space-y-0.5">
        {NAVIGATION.map((item) => (
          <NavEntry key={item.to} item={item} onNavigate={onNavigate} />
        ))}
      </ul>
    </nav>
  )
}

function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme()
  const next = resolvedTheme === 'dark' ? 'light' : 'dark'
  return (
    <Button variant="ghost" size="icon" aria-label={`Switch to ${next} theme`} onClick={() => setTheme(next)}>
      {resolvedTheme === 'dark' ? <Sun aria-hidden /> : <Moon aria-hidden />}
    </Button>
  )
}

export function AppLayout() {
  const { status, user, logout, signOutTarget } = useAuth()
  const location = useLocation()
  const [drawerOpen, setDrawerOpen] = useState(false)
  useSyncThemeFromPreferences()

  if (status === 'loading') {
    return (
      <div className="flex min-h-svh items-center justify-center" role="status" aria-label="Loading">
        <Spinner className="size-6" />
      </div>
    )
  }
  if (status === 'anonymous') {
    return <Navigate to={signOutTarget ?? loginPath(location.pathname + location.search)} replace />
  }

  return (
    <div className="min-h-svh bg-background">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-background focus:p-2">
        Skip to content
      </a>
      <aside className="fixed inset-y-0 left-0 hidden w-64 overflow-y-auto border-r bg-sidebar p-4 lg:block">
        <div className="mb-6 px-3 text-lg font-semibold">FinTrack</div>
        <Sidebar />
      </aside>
      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 flex h-14 items-center gap-2 border-b bg-background/95 px-4 backdrop-blur">
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            aria-label="Open navigation menu"
            onClick={() => setDrawerOpen(true)}
          >
            <Menu aria-hidden />
          </Button>
          <span className="font-semibold lg:hidden">FinTrack</span>
          <div className="ml-auto flex items-center gap-1">
            <span className="hidden text-sm text-muted-foreground sm:inline">{user?.full_name}</span>
            <ThemeToggle />
            <Button variant="ghost" size="icon" aria-label="Sign out" onClick={() => void logout()}>
              <LogOut aria-hidden />
            </Button>
          </div>
        </header>
        <main id="main" className="mx-auto w-full max-w-7xl min-w-0 p-4 sm:p-6">
          <Outlet />
        </main>
      </div>
      <Sheet open={drawerOpen} onOpenChange={setDrawerOpen}>
        <SheetContent side="left" className="w-72 overflow-y-auto bg-sidebar p-4">
          <SheetHeader className="p-0 pb-4">
            <SheetTitle>FinTrack</SheetTitle>
          </SheetHeader>
          <Sidebar onNavigate={() => setDrawerOpen(false)} />
        </SheetContent>
      </Sheet>
    </div>
  )
}
