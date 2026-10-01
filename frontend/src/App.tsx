import { useAuth } from '@clerk/react'
import type { ReactNode } from 'react'
import { BrowserRouter, Link, Navigate, Outlet, Route, Routes } from 'react-router'
import { AppShell } from '@/components/AppShell'
import { Button } from '@/components/ui/button'
import { useMe } from '@/lib/api'
import { useT } from '@/lib/i18n'
import Home from '@/pages/Home'
import Landing from '@/pages/Landing'

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
            {/* Filled in later branches: 08 onboarding, 09 player, 10 settings, 12 admin. */}
            <Route path="/onboarding" element={<Placeholder title="page.onboarding" />} />
            <Route path="/episodes/:id" element={<Placeholder title="page.episode" />} />
            <Route path="/settings" element={<Placeholder title="page.settings" />} />
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
  if (!isLoaded) return null
  return isSignedIn ? <Outlet /> : fallback
}

function RequireAuth() {
  return <SignedInOr fallback={<Navigate to="/" replace />} />
}

function AdminOnly() {
  const { data: me } = useMe()
  if (!me) return null
  // UI gate only; the API enforces the admin role on /admin/* itself.
  return me.is_admin ? <Placeholder title="page.admin" /> : <NotFound />
}

function Placeholder({ title }: { title: Parameters<ReturnType<typeof useT>['t']>[0] }) {
  const { t } = useT()
  return <h1 className="text-4xl">{t(title)}</h1>
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
