import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Suspense, lazy } from 'react'
import { Navigate, Outlet, createBrowserRouter, type RouteObject } from 'react-router'

import { Toaster } from '@/components/ui/sonner'
import { TooltipProvider } from '@/components/ui/tooltip'
import { AccountsPage } from '@/features/accounts/AccountsPage'
import { AuthProvider } from '@/features/auth/AuthProvider'
import { ForgotPasswordPage } from '@/features/auth/ForgotPasswordPage'
import { LoginPage } from '@/features/auth/LoginPage'
import { RegisterPage } from '@/features/auth/RegisterPage'
import { ResetPasswordPage } from '@/features/auth/ResetPasswordPage'
import { ChangePasswordForm } from '@/features/auth/ChangePasswordForm'
import { CategoriesPage } from '@/features/categories/CategoriesPage'
import { DeleteAccountSection } from '@/features/settings/DeleteAccountSection'
import { PreferencesSection } from '@/features/settings/PreferencesSection'
import { ProfileSection } from '@/features/settings/ProfileSection'
import { SettingsPage } from '@/features/settings/SettingsPage'
import { ImportWizard } from '@/features/transactions/ImportWizard'
import { TransactionsPage } from '@/features/transactions/TransactionsPage'
import { AppLayout } from '@/layouts/AppLayout'
import { ComingSoon } from '@/pages/ComingSoon'
import { NotFound } from '@/pages/NotFound'

import { LoadingBlock } from '@/components/common/states'

import { COMING_SOON_ROUTES } from './navigation'

// Chart-heavy pages are code-split so Recharts loads only when needed.
const OverviewPage = lazy(() => import('@/features/dashboard/OverviewPage').then((m) => ({ default: m.OverviewPage })))
const ReportsPage = lazy(() => import('@/features/reports/ReportsPage').then((m) => ({ default: m.ReportsPage })))
const IncomePage = lazy(() => import('@/features/reports/IncomePage').then((m) => ({ default: m.IncomePage })))
const ExpensesPage = lazy(() => import('@/features/reports/ExpensesPage').then((m) => ({ default: m.ExpensesPage })))
const BudgetsPage = lazy(() => import('@/features/budgets/BudgetsPage').then((m) => ({ default: m.BudgetsPage })))
const GoalsPage = lazy(() => import('@/features/goals/GoalsPage').then((m) => ({ default: m.GoalsPage })))
const NetWorthPage = lazy(() => import('@/features/networth/NetWorthPage').then((m) => ({ default: m.NetWorthPage })))
const LoansPage = lazy(() => import('@/features/loans/LoansPage').then((m) => ({ default: m.LoansPage })))

function Lazy({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<LoadingBlock label="Loading page" />}>{children}</Suspense>
}
import { ThemeProvider } from './theme'

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: 1, refetchOnWindowFocus: false, staleTime: 30_000 },
      mutations: { retry: 0 },
    },
  })
}

/** Providers that need router context (auth navigates on session loss). */
export function RootProviders({ queryClient }: { queryClient: QueryClient }) {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <TooltipProvider>
          <AuthProvider>
            <Outlet />
            <Toaster position="top-right" richColors closeButton />
          </AuthProvider>
        </TooltipProvider>
      </ThemeProvider>
    </QueryClientProvider>
  )
}

export function appRoutes(queryClient: QueryClient): RouteObject[] {
  return [
    {
      element: <RootProviders queryClient={queryClient} />,
      children: [
        { path: '/login', element: <LoginPage /> },
        { path: '/register', element: <RegisterPage /> },
        { path: '/forgot-password', element: <ForgotPasswordPage /> },
        { path: '/reset-password', element: <ResetPasswordPage /> },
        {
          element: <AppLayout />,
          children: [
            { index: true, element: <Lazy><OverviewPage /></Lazy> },
            { path: 'transactions', element: <TransactionsPage /> },
            { path: 'transactions/import', element: <ImportWizard /> },
            { path: 'income', element: <Lazy><IncomePage /></Lazy> },
            { path: 'expenses', element: <Lazy><ExpensesPage /></Lazy> },
            { path: 'reports', element: <Lazy><ReportsPage /></Lazy> },
            { path: 'budgets', element: <Lazy><BudgetsPage /></Lazy> },
            { path: 'goals', element: <Lazy><GoalsPage /></Lazy> },
            { path: 'net-worth', element: <Lazy><NetWorthPage /></Lazy> },
            { path: 'loans', element: <Lazy><LoansPage /></Lazy> },
            { path: 'loans/:type', element: <Lazy><LoansPage /></Lazy> },
            {
              path: 'settings',
              element: <SettingsPage />,
              children: [
                { index: true, element: <Navigate to="profile" replace /> },
                { path: 'profile', element: <ProfileSection /> },
                { path: 'preferences', element: <PreferencesSection /> },
                { path: 'accounts', element: <AccountsPage /> },
                { path: 'categories', element: <CategoriesPage /> },
                { path: 'security', element: <ChangePasswordForm /> },
                { path: 'delete', element: <DeleteAccountSection /> },
              ],
            },
            ...COMING_SOON_ROUTES.map((item) => ({
              path: item.to.slice(1),
              element: <ComingSoon title={item.label} release={item.release} />,
            })),
            { path: '*', element: <NotFound /> },
          ],
        },
      ],
    },
  ]
}

export function createRouter() {
  return createBrowserRouter(appRoutes(createQueryClient()))
}
