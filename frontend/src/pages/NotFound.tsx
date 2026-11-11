import { Link } from 'react-router'

export function NotFound() {
  return (
    <div className="flex flex-col items-center gap-3 p-10 text-center">
      <h1 className="text-2xl font-semibold">Page not found</h1>
      <Link to="/" className="text-primary underline underline-offset-4">
        Back to Overview
      </Link>
    </div>
  )
}
