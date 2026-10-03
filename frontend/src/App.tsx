import { useAuth } from '@clerk/react'
import { lazy, type ReactNode, Suspense } from 'react'
import { BrowserRouter, Link, Navigate, Outlet, Route, Routes } from 'react-router'
import { AppShell } from '@/components/AppShell'
import { Logo } from '@/components/Logo'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useMe } from '@/lib/api'
import { useT } from '@/lib/i18n'
import Home from '@/pages/Home'
import Landing from '@/pages/Landing'
import Episode from '@/pages/Episode'
import Onboarding from '@/pages/Onboarding'
import Settings from '@/pages/Settings'

// Charts (Recharts) only load for admins, on /admin.
const Admin = lazy(() => import('@/pages/Admin'))

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<SignedInOr fallback={<Landing />} />}>
          <Route element={<AppShell />}>
            <Route index element={<Home />} />
          </Route>
        </Route>
        <Route element={<RequireAuth />}>
          <Route element={<AppShell />}>
            {/* Filled in a later branch: 12 admin. */}
            <Route path="/onboarding" element={<Onboarding />} />
            <Route path="/episodes/:id" element={<Episode />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/admin" element={<AdminOnly />} />
          </Route>
        </Route>
        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  )
}

/** Renders the nested routes when signed in, `fallback` otherwise (the landing at `/`). */
function SignedInOr({ fallback }: { fallback: ReactNode }) {
  const { isLoaded, isSignedIn } = useAuth()
  if (!isLoaded)
    return (
      <div className="grid min-h-svh place-items-center">
        <Logo />
      </div>
    )
  return isSignedIn ? <Outlet /> : fallback
}

function RequireAuth() {
  return <SignedInOr fallback={<Navigate to="/" replace />} />
}

function AdminOnly() {
  const { data: me } = useMe()
  if (!me) return null
  // UI gate only; the API enforces the admin role on /admin/* itself.
  if (!me.is_admin) return <NotFound />
  return (
    <Suspense fallback={<Skeleton className="h-96 w-full" />}>
      <Admin />
    </Suspense>
  )
}

function NotFound() {
  const { t } = useT()
  return (
    <main className="grid min-h-svh place-content-center gap-4 p-4 text-center">
      <h1 className="text-5xl">{t('page.notFound')}</h1>
      <p className="text-muted-foreground">{t('page.notFoundBody')}</p>
      <Button asChild variant="outline" className="justify-self-center">
        <Link to="/">{t('page.backHome')}</Link>
      </Button>
    </main>
  )
}
