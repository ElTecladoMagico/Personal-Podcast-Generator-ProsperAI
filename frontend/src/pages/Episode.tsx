import { useEffect, useMemo, useRef, useState } from 'react'
import { useParams } from 'react-router'
import { EpisodeCover } from '@/components/EpisodeCover'
import { GenerationProgress } from '@/components/GenerationProgress'
import { ChapterBar } from '@/components/player/ChapterBar'
import { Controls } from '@/components/player/Controls'
import { Hosts } from '@/components/player/Hosts'
import { StoryCard } from '@/components/player/StoryCard'
import { Transcript } from '@/components/player/Transcript'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { coverSeed, type EpisodeDetail, useEpisode } from '@/lib/episodes'
import { useT } from '@/lib/i18n'
import { chapterSegments, isSkip, locate, type Script } from '@/lib/timeline'
import { useAudio } from '@/lib/useAudio'
import { useTrack } from '@/lib/useTrack'

export default function Episode() {
  const { id } = useParams()
  const { t } = useT()
  const { data: episode, error, refetch } = useEpisode(id)
  if (error)
    return (
      <div className="space-y-3">
        <p>{t('player.error')}</p>
        <Button variant="outline" onClick={() => refetch()}>{t('player.retry')}</Button>
      </div>
    )
  if (!episode) return <Skeleton className="h-96 w-full" />
  if (episode.status !== 'ready' || !episode.script) return <div className="mx-auto max-w-xl"><GenerationProgress episode={episode} /></div>
  return <Player episode={episode} script={episode.script} />
}

function Player({ episode, script }: { episode: EpisodeDetail; script: Script }) {
  const { t } = useT()
  const { ref: audioRef, ...player } = useAudio()
  const duration = player.duration || episode.duration_s || 0
  const { track, progress, seen } = useTrack(episode.id, duration)
  const position = locate(script, player.time)
  const segments = useMemo(() => chapterSegments(script, duration), [script, duration])
  const chapter = script.chapters[position.chapter]
  const speaker = chapter?.turns[position.turn]?.speaker ?? 0
  const sources = useMemo(() => episode.sources ?? {}, [episode.sources])
  const [votes, setVotes] = useState(episode.votes) // saved ones, so a reload keeps them

  // --- analytics ------------------------------------------------------------------
  const started = useRef(false)
  const lastChapter = useRef(-1)
  useEffect(() => {
    seen(player.time)
  }, [player.time, seen])
  useEffect(() => {
    if (player.playing && !started.current) {
      started.current = true
      track('play_started', { position_s: Math.round(player.time) })
    }
    if (!player.playing && started.current) progress()
  }, [player.playing]) // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!player.playing || position.chapter === lastChapter.current) return
    lastChapter.current = position.chapter
    track('chapter_started', { chapter_index: position.chapter, story_id: chapter?.story_id ?? null })
  }, [player.playing, position.chapter, chapter?.story_id, track])

  const trackSkip = (ci: number) => {
    const { story_id, start_s } = script.chapters[ci]
    if (story_id) track('chapter_skipped', { chapter_index: ci, story_id, after_s: Math.round(player.time - (start_s ?? 0)) })
  }
  // Scrubbing counts as a skip only past half the chapter; "next chapter" always does.
  const seek = (to: number) => {
    const skipped = isSkip(script, player.time, to)
    if (skipped !== null) trackSkip(skipped)
    player.seek(to)
  }
  const goToChapter = (delta: number) => {
    const next = segments[position.chapter + delta]
    if (!next) return
    if (delta > 0) trackSkip(position.chapter)
    player.seek(next.start)
  }
  const vote = (value: 'up' | 'down') => {
    if (!chapter?.story_id) return
    setVotes((v) => ({ ...v, [chapter.story_id!]: value }))
    track('feedback', { story_id: chapter.story_id, value })
  }

  // --- keyboard and system media controls -------------------------------------------
  const actions = useRef({ seek, goToChapter, toggle: player.toggle, time: player.time })
  useEffect(() => {
    actions.current = { seek, goToChapter, toggle: player.toggle, time: player.time }
  })
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement).closest('input, textarea, select, [contenteditable]')) return
      const a = actions.current
      const step = e.key === 'ArrowLeft' ? -1 : e.key === 'ArrowRight' ? 1 : 0
      if (e.code === 'Space') {
        e.preventDefault()
        a.toggle()
      } else if (step && e.shiftKey) a.goToChapter(step)
      else if (step) a.seek(a.time + step * 5)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])
  useMediaSession(episode, audioRef, actions)

  const storySources = Object.values(sources).filter((s) => s.story_id === chapter?.story_id)
  const isLast = position.chapter >= script.chapters.length - 1
  return (
    <div className="relative">
      {episode.audio_url && <audio ref={audioRef} src={episode.audio_url} preload="metadata" />}
      <Backdrop id={episode.id} playing={player.playing} />
      <div className="grid gap-8 lg:grid-cols-[minmax(0,420px)_1fr]">
        <section className="space-y-5 lg:sticky lg:top-20 lg:self-start">
          {chapter?.story_id ? (
            <StoryCard chapter={chapter} sources={storySources} vote={votes[chapter.story_id]} onVote={vote}
              onSkip={isLast ? undefined : () => goToChapter(1)} />
          ) : (
            <EpisodeCover id={episode.id} topics={episode.topics} className="w-full max-w-sm" />
          )}
          <div>
            <h1 className="text-3xl leading-tight sm:text-4xl">{script.title}</h1>
            <p className="mt-1 text-sm text-muted-foreground">{script.summary}</p>
          </div>
          <Hosts names={episode.hosts} speaking={speaker} playing={player.playing} />
          {episode.audio_url ? (
            // On phones the transcript sits below, so the controls stay pinned to the bottom.
            <div className="space-y-2 max-lg:fixed max-lg:inset-x-0 max-lg:bottom-0 max-lg:z-20 max-lg:border-t max-lg:bg-background/90 max-lg:px-4 max-lg:pt-3 max-lg:pb-[max(0.75rem,env(safe-area-inset-bottom))] max-lg:backdrop-blur">
              <ChapterBar segments={segments} time={player.time} active={position.chapter} onSeek={seek} />
              <Controls playing={player.playing} time={player.time} duration={duration} rate={player.rate}
                onToggle={player.toggle} onSeek={seek} onRate={player.setRate} />
            </div>
          ) : (
            <p className="rounded-lg border border-signal/40 p-3 text-sm text-muted-foreground">{t('player.expired')}</p>
          )}
        </section>
        <section className="min-w-0 max-lg:pb-36">
          <Transcript script={script} hosts={episode.hosts} position={position} sources={sources} onSeek={seek} />
        </section>
      </div>
    </div>
  )
}

/** Soft colours from the cover behind everything; it breathes while the audio plays. */
function Backdrop({ id, playing }: { id: string; playing: boolean }) {
  const hue = [35, 75, 195, 255, 320][coverSeed(id) % 5]
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <div className={`absolute -top-40 left-1/4 size-[36rem] rounded-full blur-3xl transition-opacity duration-1000 ${playing ? 'opacity-30 motion-safe:animate-pulse' : 'opacity-15'}`}
        style={{ background: `oklch(0.6 0.15 ${hue})` }} />
    </div>
  )
}

type Actions = { current: { seek: (t: number) => void; goToChapter: (d: number) => void; toggle: () => void; time: number } }

/** Lock screen, headphones and media keys control the player (Media Session API). */
function useMediaSession(episode: EpisodeDetail, audioRef: { current: HTMLAudioElement | null }, actions: Actions) {
  useEffect(() => {
    if (!('mediaSession' in navigator)) return
    navigator.mediaSession.metadata = new MediaMetadata({
      title: episode.title ?? 'Personal Podcast',
      artist: 'Personal Podcast',
      album: new Date(episode.created_at).toLocaleDateString(),
    })
    const handlers: [MediaSessionAction, MediaSessionActionHandler][] = [
      ['play', () => void audioRef.current?.play()],
      ['pause', () => audioRef.current?.pause()],
      ['seekbackward', () => actions.current.seek(actions.current.time - 15)],
      ['seekforward', () => actions.current.seek(actions.current.time + 30)],
      ['previoustrack', () => actions.current.goToChapter(-1)],
      ['nexttrack', () => actions.current.goToChapter(1)],
      ['seekto', (d) => d.seekTime != null && actions.current.seek(d.seekTime)],
    ]
    for (const [action, handler] of handlers) navigator.mediaSession.setActionHandler(action, handler)
    return () => {
      for (const [action] of handlers) navigator.mediaSession.setActionHandler(action, null)
    }
  }, [episode.title, episode.created_at, audioRef, actions])
}
