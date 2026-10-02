import type { Segment } from '@/lib/timeline'
import { cn } from '@/lib/utils'

/** Progress split by chapter: each segment fills as it plays; click jumps to its start. */
export function ChapterBar({ segments, time, active, onSeek }: {
  segments: Segment[]
  time: number
  active: number
  onSeek: (t: number) => void
}) {
  return (
    <div className="flex h-8 items-center gap-1" role="group">
      {segments.map((s) => {
        const fill = Math.min(Math.max((time - s.start) / (s.end - s.start || 1), 0), 1)
        return (
          <button key={s.index} type="button" title={s.title} aria-label={s.title} onClick={() => onSeek(s.start)}
            className="group relative h-full min-w-2 flex-auto" style={{ flexBasis: `${s.width}%` }}>
            <span className={cn('absolute inset-x-0 top-1/2 h-1.5 -translate-y-1/2 overflow-hidden rounded-full bg-muted transition-[height] group-hover:h-2.5',
              s.index === active && 'h-2')}>
              <span className="block h-full bg-primary" style={{ width: `${fill * 100}%` }} />
            </span>
          </button>
        )
      })}
    </div>
  )
}
