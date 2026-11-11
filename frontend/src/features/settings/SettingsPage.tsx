import { NavLink, Outlet } from 'react-router'

import { PageHeader } from '@/components/common/states'
import { cn } from '@/lib/utils'

const TABS = [
  { to: 'profile', label: 'Profile' },
  { to: 'preferences', label: 'Preferences' },
  { to: 'accounts', label: 'Accounts' },
  { to: 'categories', label: 'Categories' },
  { to: 'security', label: 'Security' },
  { to: 'delete', label: 'Delete account' },
]

export function SettingsPage() {
  return (
    <div>
      <PageHeader title="Settings" description="Profile, preferences, money accounts and categories." />
      <nav aria-label="Settings sections" className="-mx-1 mb-6 overflow-x-auto">
        <ul className="flex gap-1 border-b px-1">
          {TABS.map((t) => (
            <li key={t.to}>
              <NavLink
                to={t.to}
                className={({ isActive }) =>
                  cn(
                    'inline-block border-b-2 px-3 py-2 text-sm whitespace-nowrap outline-none focus-visible:ring-2 focus-visible:ring-ring',
                    isActive ? 'border-primary font-medium text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground',
                  )
                }
              >
                {t.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      <Outlet />
    </div>
  )
}
