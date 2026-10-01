import { Navigate } from 'react-router'
import { Skeleton } from '@/components/ui/skeleton'
import { useMe } from '@/lib/api'
import { useT } from '@/lib/i18n'

export default function Home() {
  const { t } = useT()
  const { data: me, error } = useMe()

  if (error) return <p className="text-destructive">{t('error.generic')}: {error.message}</p>
  if (!me) return <Skeleton className="h-12 w-72" />
  if (!me.onboarded) return <Navigate to="/onboarding" replace />

  return (
    <section className="space-y-2">
      <p className="text-muted-foreground">
        {t('home.hello')}, {me.display_name ?? me.email}
      </p>
      <h1 className="text-4xl">{t('page.home')}</h1>
    </section>
  )
}
