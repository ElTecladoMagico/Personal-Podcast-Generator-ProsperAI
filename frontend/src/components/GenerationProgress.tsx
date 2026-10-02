import { BookOpen, Check, Clock, Mic, Newspaper, PenLine, Play, Radio, SearchCheck, X } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { Link } from 'react-router'
import { Button } from '@/components/ui/button'
import { type EpisodeDetail, type Stage, STAGES, stageStates, useRetry } from '@/lib/episodes'
import { format, useT } from '@/lib/i18n'
import { cn } from '@/lib/utils'

const ICONS: Record<Stage, LucideIcon> = {
  queued: Clock,
  fetching: Radio,
  editing: Newspaper,
  researching: BookOpen,
  writing: PenLine,
  verifying: SearchCheck,
  recording: Mic,
}

/** The newsroom at work: every stage with what it really found, updated by polling. */
export function GenerationProgress({ episode }: { episode: EpisodeDetail }) {
  const { t } = useT()
  const retry = useRetry()
  const states = stageStates(episode.status, episode.failed_stage)
  const p = episode.progress
  const active = STAGES.find((s) => states[s] === 'active' || states[s] === 'failed')

  const detail: Partial<Record<Stage, string>> = {
    fetching: p.candidates ? format(t('stage.detail.fetching'), { candidates: p.candidates, outlets: p.outlets }) : undefined,
    editing: p.stories.length ? format(t('stage.detail.editing'), { n: p.stories.length }) : undefined,
    researching: p.articles ? format(t('stage.detail.researching'), { n: p.articles }) : undefined,
    verifying:
      p.issues_found == null
        ? undefined
        : p.issues_found === 0
          ? t('stage.detail.verifyingOk')
          : format(t('stage.detail.verifyingFixed'), { found: p.issues_found, fixed: p.issues_fixed ?? 0 }),
    recording: p.recording ? format(t('stage.detail.recording'), p.recording) : undefined,
  }

  return (
    <div className="space-y-6">
      <p className="sr-only" aria-live="polite">
        {active ? t(`stage.${active}`) : episode.status === 'ready' ? t('stage.ready') : ''}
      </p>
      {episode.status === 'ready' && (
        <Button asChild size="lg">
          <Link to={`/episodes/${episode.id}`}>
            <Play /> {t('home.listen')}
          </Link>
        </Button>
      )}
      <ol className="space-y-1">
        {STAGES.map((stage) => {
          const state = states[stage]
          const Icon = ICONS[stage]
          return (
            <li
              key={stage}
              className={cn(
                'flex gap-4 rounded-lg px-3 py-2.5 transition-colors duration-300',
                state === 'active' && 'bg-accent',
                state === 'pending' && 'opacity-45',
              )}
            >
              <span
                className={cn(
                  'relative mt-0.5 grid size-7 shrink-0 place-items-center rounded-full border',
                  state === 'done' && 'border-transparent bg-primary/15 text-primary',
                  state === 'active' && 'border-primary text-primary',
                  state === 'failed' && 'border-destructive text-destructive',
                )}
              >
                {state === 'active' && (
                  <span className="absolute inset-0 rounded-full bg-primary/30 motion-safe:animate-ping" />
                )}
                {state === 'done' ? <Check className="size-4" /> : state === 'failed' ? <X className="size-4" /> : <Icon className="size-4" />}
              </span>
              <div className="min-w-0 flex-1 space-y-1">
                <p className={cn('font-medium', state === 'active' && 'text-foreground')}>{t(`stage.${stage}`)}</p>
                {detail[stage] && state !== 'pending' && (
                  <p className="text-sm text-muted-foreground motion-safe:animate-in motion-safe:fade-in">{detail[stage]}</p>
                )}
                {stage === 'editing' && state !== 'pending' && p.stories.length > 0 && (
                  <ul className="space-y-0.5 pt-1">
                    {p.stories.map((headline, i) => (
                      <li
                        key={headline}
                        className="text-sm text-foreground/90 motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-left-2 motion-safe:fill-mode-both"
                        style={{ animationDelay: `${i * 120}ms` }}
                      >
                        · {headline}
                      </li>
                    ))}
                  </ul>
                )}
                {stage === 'recording' && state === 'active' && p.recording && (
                  <div className="h-1 overflow-hidden rounded-full bg-muted" role="progressbar"
                    aria-valuenow={p.recording.done} aria-valuemax={p.recording.total}>
                    <div className="h-full bg-primary transition-[width] duration-700"
                      style={{ width: `${(100 * p.recording.done) / p.recording.total}%` }} />
                  </div>
                )}
              </div>
            </li>
          )
        })}
      </ol>

      {episode.status === 'failed' && (
        <div className="flex flex-wrap items-center gap-3 rounded-lg border border-destructive/40 p-4">
          <p className="flex-1 text-sm">{format(t('stage.failed'), { stage: t(`stage.${(episode.failed_stage ?? 'queued') as Stage}`) })}</p>
          <Button variant="outline" onClick={() => retry.mutate(episode.id)} disabled={retry.isPending}>
            {t('stage.retry')}
          </Button>
        </div>
      )}
    </div>
  )
}
