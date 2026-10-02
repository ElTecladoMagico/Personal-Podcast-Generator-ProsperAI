import { Play, Radio } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, Navigate } from 'react-router'
import { toast } from 'sonner'
import { EpisodeCover } from '@/components/EpisodeCover'
import { GenerationProgress } from '@/components/GenerationProgress'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { ApiError, useMe } from '@/lib/api'
import { type EpisodeSummary, greetingKey, isTerminal, useEpisode, useEpisodes, useGenerate } from '@/lib/episodes'
import { useT } from '@/lib/i18n'
import { useQueryClient } from '@tanstack/react-query'

export default function Home() {
  const { t } = useT()
  const { data: me, error } = useMe()
  const episodes = useEpisodes()
  const generate = useGenerate()
  const queryClient = useQueryClient()

  // The newest episode gets the big card: live progress while it is being made.
  const latest = episodes.data?.[0]
  const live = useEpisode(latest?.id)
  const producing = Boolean(latest) && !isTerminal(live.data?.status ?? latest?.status)
  // An episode you watched being made keeps its progress list (ending in "Listen");
  // one that was already ready when you arrived just shows the button.
  const [watched, setWatched] = useState<string>()
  const [hour] = useState(() => new Date().getHours())
  if (producing && latest && watched !== latest.id) setWatched(latest.id)
  useEffect(() => {
    if (live.data && isTerminal(live.data.status)) queryClient.invalidateQueries({ queryKey: ['episodes'] })
  }, [live.data, queryClient])

  if (error) return <p className="text-destructive">{t('error.generic')}: {error.message}</p>
  if (!me || episodes.isPending) return <Skeleton className="h-64 w-full" />
  if (!me.onboarded) return <Navigate to="/onboarding" replace />

  const onGenerate = () =>
    generate.mutate(undefined, {
      onError: (err) => {
        const status = err instanceof ApiError ? err.status : 0
        toast.error(status === 409 ? t('home.errorBusy') : status === 429 ? t('home.errorLimit') : err.message)
      },
    })

  const name = me.display_name ?? me.email ?? ''
  return (
    <div className="space-y-10">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="space-y-1">
          <p className="text-muted-foreground">
            {t(greetingKey(hour))}
            {name && `, ${name}`}
          </p>
          <h1 className="text-4xl sm:text-5xl">{t('page.home')}</h1>
        </div>
        <Button size="lg" onClick={onGenerate} disabled={producing || generate.isPending}>
          <Radio className={producing ? 'motion-safe:animate-pulse' : ''} />
          {producing ? t('home.generating') : t('home.generate')}
        </Button>
      </header>

      {!latest && <EmptyState />}

      {latest && (
        <section className="grid gap-6 rounded-2xl border bg-card p-5 sm:p-6 md:grid-cols-[240px_1fr]">
          <EpisodeCover id={latest.id} topics={live.data?.topics ?? latest.topics} className="w-32 md:w-full md:max-w-60" />
          <div className="min-w-0 space-y-4">
            <div>
              <p className="text-xs tracking-widest text-muted-foreground uppercase">{dateLabel(latest)}</p>
              <h2 className="text-3xl">
                {live.data?.title ?? latest.title ?? (live.data?.status === 'failed' ? t('error.generic') : t('home.generating'))}
              </h2>
              {(live.data?.summary ?? latest.summary) && <p className="mt-1 text-muted-foreground">{live.data?.summary ?? latest.summary}</p>}
            </div>
            {live.data && (producing || watched === latest.id) ? (
              <GenerationProgress episode={live.data} />
            ) : (
              <Button asChild size="lg">
                <Link to={`/episodes/${latest.id}`}>
                  <Play /> {t('home.listen')}
                </Link>
              </Button>
            )}
          </div>
        </section>
      )}

      {episodes.data && episodes.data.length > 1 && (
        <section className="space-y-4">
          <h2 className="text-2xl">{t('home.previous')}</h2>
          <ul className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
            {episodes.data.slice(1).map((ep) => (
              <li key={ep.id}>
                <Link to={`/episodes/${ep.id}`} className="group block space-y-2 rounded-xl outline-none focus-visible:ring-2 focus-visible:ring-ring">
                  <EpisodeCover id={ep.id} topics={ep.topics} className="transition-transform duration-200 group-hover:scale-[1.02]" />
                  <p className="line-clamp-2 text-sm font-medium">{ep.title ?? (ep.status === 'failed' ? t('error.generic') : t('home.generating'))}</p>
                  <p className="text-xs text-muted-foreground">
                    {dateLabel(ep)}
                    {ep.duration_s ? ` · ${Math.round(ep.duration_s / 60)} ${t('home.min')}` : ''}
                  </p>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}

function dateLabel(ep: EpisodeSummary) {
  return new Date(ep.created_at).toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long' })
}

function EmptyState() {
  const { t } = useT()
  return (
    <section className="grid place-items-center gap-3 rounded-2xl border border-dashed p-12 text-center">
      <Radio className="size-10 text-primary" />
      <h2 className="text-3xl">{t('home.emptyTitle')}</h2>
      <p className="max-w-md text-muted-foreground">{t('home.emptyBody')}</p>
    </section>
  )
}
