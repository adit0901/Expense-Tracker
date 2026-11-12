import {
  ArrowLeftRight,
  BarChart3,
  Bot,
  Gauge,
  Landmark,
  LayoutDashboard,
  PiggyBank,
  Receipt,
  Scale,
  Settings,
  TrendingUp,
  Wallet,
  type LucideIcon,
} from 'lucide-react'

export interface NavItem {
  label: string
  to: string
  icon?: LucideIcon
  /** Unreleased capabilities render a coming-soon page and call no APIs. */
  release?: 'P1' | 'P2' | 'P3'
  children?: NavItem[]
}

export const NAVIGATION: NavItem[] = [
  { label: 'Overview', to: '/', icon: LayoutDashboard },
  { label: 'Transactions', to: '/transactions', icon: ArrowLeftRight },
  { label: 'Income', to: '/income', icon: Wallet },
  { label: 'Expenses', to: '/expenses', icon: Receipt },
  { label: 'Budgets', to: '/budgets', icon: Gauge },
  { label: 'Savings & Goals', to: '/goals', icon: PiggyBank },
  {
    label: 'Investments',
    to: '/investments',
    icon: TrendingUp,
    release: 'P2',
    children: [
      { label: 'Indian Stocks', to: '/investments/indian-stocks', release: 'P2' },
      { label: 'US Stocks', to: '/investments/us-stocks', release: 'P2' },
      { label: 'Portfolio Overview', to: '/investments/portfolio', release: 'P2' },
    ],
  },
  {
    label: 'Loans & EMIs',
    to: '/loans',
    icon: Landmark,
    children: [
      { label: 'Home Loans', to: '/loans/home' },
      { label: 'Car Loans', to: '/loans/car' },
      { label: 'Other Loans', to: '/loans/other' },
    ],
  },
  { label: 'Net Worth', to: '/net-worth', icon: Scale },
  { label: 'Reports & Analytics', to: '/reports', icon: BarChart3 },
  { label: 'AI Financial Assistant', to: '/assistant', icon: Bot, release: 'P3' },
  { label: 'Settings', to: '/settings', icon: Settings },
]

export const COMING_SOON_ROUTES: NavItem[] = NAVIGATION.flatMap((item) =>
  item.children ? [item, ...item.children] : [item],
).filter((item) => item.release)
