import { memo, useEffect, useMemo, useRef } from 'react'
import type { components } from '@/lib/api-types'
import { format, useT } from '@/lib/i18n'
import { type Position, type Script, spokenText, type Turn } from '@/lib/timeline'
import { cn } from '@/lib/utils'
import { hostColor } from './hostColor'

type Sources = Record<string, components['schemas']['Source']>

/** The script, live: the word being spoken lights up; clicking a word or a turn seeks there. */
export function Transcript({ script, hosts, position, sources, onSeek }: {
  script: Script
  hosts: string[]
  position: Position
  sources: Sources
  onSeek: (t: number) => void
}) {
  const { t } = useT()
  const container = useRef<HTMLOListElement>(null)
  const active = useRef<HTMLLIElement | null>(null)
  const userScrolledAt = useRef(0)
  const sourceNumber = useMemo(() => Object.fromEntries(Object.keys(sources).map((id, i) => [id, i + 1])), [sources])

  // Keep the active turn centred, unless the listener scrolled by hand in the last 4 s.
  useEffect(() => {
    if (Date.now() - userScrolledAt.current < 4000) return
    active.current?.scrollIntoView({ block: 'center', behavior: 'smooth' })
  }, [position.chapter, position.turn])

  return (
    <ol ref={container} aria-label={t('player.transcript')} className="space-y-6"
      onWheel={() => (userScrolledAt.current = Date.now())} onTouchMove={() => (userScrolledAt.current = Date.now())}>
      {script.chapters.map((chapter, ci) => (
        <li key={ci} className="space-y-3">
          <h2 className="text-xs tracking-widest text-muted-foreground uppercase">{chapter.title}</h2>
          <ol className="space-y-3">
            {chapter.turns.map((turn, ti) => {
              const isActive = ci === position.chapter && ti === position.turn
              return (
                <TurnRow key={ti} turn={turn} host={hosts[turn.speaker] ?? ''} active={isActive}
                  word={isActive ? position.word : -1} sourceNumber={sourceNumber} sources={sources} onSeek={onSeek}
                  rowRef={isActive ? (el) => { active.current = el } : undefined} sourceLabel={t('player.source')} />
              )
            })}
          </ol>
        </li>
      ))}
    </ol>
  )
}

const TurnRow = memo(function TurnRow({ turn, host, active, word, sourceNumber, sources, onSeek, rowRef, sourceLabel }: {
  turn: Turn
  host: string
  active: boolean
  word: number
  sourceNumber: Record<string, number>
  sources: Sources
  onSeek: (t: number) => void
  rowRef?: (el: HTMLLIElement | null) => void
  sourceLabel: string
}) {
  return (
    <li ref={rowRef} aria-current={active || undefined}
      className={cn('flex gap-3 rounded-lg p-2 transition-colors duration-300', active ? 'bg-accent/70' : 'text-foreground/75 hover:text-foreground')}>
      <span className="mt-1 size-2 shrink-0 rounded-full" style={{ background: hostColor(turn.speaker) }} aria-hidden />
      <div className="min-w-0 space-y-1">
        <button type="button" onClick={() => onSeek(turn.start_s ?? 0)} className="text-xs font-medium text-muted-foreground hover:text-foreground">
          {host}
        </button>
        {/* One click handler per turn; each word carries its start (keyboard users seek via the host button). */}
        <p className="cursor-pointer leading-relaxed"
          onClick={(e) => {
            const el = e.target as HTMLElement
            if (!el.closest('a')) onSeek(Number(el.dataset.t ?? turn.start_s ?? 0))
          }}>
          {turn.words?.length
            ? turn.words.map(([start, w], i) => (
                <span key={i}>
                  <span data-t={start}
                    className={cn('rounded-sm transition-colors', i === word ? 'bg-primary/25 text-foreground' : i < word && active ? 'text-foreground' : '')}>
                    {w}
                  </span>{' '}
                </span>
              ))
            : spokenText(turn.text)}
          {turn.source_ids.map((id) =>
            sources[id] ? (
              <a key={id} href={sources[id].url} target="_blank" rel="noreferrer"
                aria-label={format(sourceLabel, { n: sourceNumber[id], title: sources[id].title })}
                className="ml-0.5 align-super text-[0.65rem] text-primary hover:underline">
                {sourceNumber[id]}
              </a>
            ) : null,
          )}
        </p>
      </div>
    </li>
  )
})
