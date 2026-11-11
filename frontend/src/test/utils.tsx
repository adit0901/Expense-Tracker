import { render } from '@testing-library/react'
import { RouterProvider, createMemoryRouter } from 'react-router'

import { appRoutes, createQueryClient } from '@/app/router'

/** Render the real route tree at `path` (auth restores via the mocked refresh endpoint). */
export function renderApp(path: string) {
  const queryClient = createQueryClient()
  queryClient.setDefaultOptions({ queries: { retry: false, staleTime: 0 } })
  const router = createMemoryRouter(appRoutes(queryClient), { initialEntries: [path] })
  const utils = render(<RouterProvider router={router} />)
  return { ...utils, router, queryClient }
}
