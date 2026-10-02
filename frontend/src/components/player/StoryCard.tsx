import { SkipForward, ThumbsDown, ThumbsUp } from 'lucide-react'
import { Button } from '@/components/ui/button'
import type { components } from '@/lib/api-types'
import { format, useT } from '@/lib/i18n'
import type { Chapter } from '@/lib/timeline'
import { cn } from '@/lib/utils'

type Source = components['schemas']['Source']
const favicon = (url: string) => `https://www.google.com/s2/favicons?domain=${new URL(url).hostname}&sz=64`

/** The story being told: picture, headline, the outlets behind it, and what you think of it. */
export function StoryCard({ chapter, sources, vote, onVote, onSkip }: {
  chapter: Chapter
  sources: Source[]
  vote: 'up' | 'down' | undefined
  onVote: (value: 'up' | 'down') => void
  onSkip?: () => void
}) {
  const { t } = useT()
  const image = sources.find((s) => s.image_url)?.image_url
  return (
    <article key={chapter.story_id} className="overflow-hidden rounded-2xl border bg-card motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-2 motion-safe:duration-500">
      {image && <img src={image} alt="" className="aspect-[2/1] w-full object-cover" loading="lazy" referrerPolicy="no-referrer" />}
      <div className="space-y-3 p-4">
        <h2 className="text-2xl leading-tight">{chapter.title}</h2>
        <ul className="flex flex-wrap gap-2">
          {sources.map((s) => (
            <li key={s.url}>
              <a href={s.url} target="_blank" rel="noreferrer" className="flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs text-muted-foreground hover:text-foreground">
                <img src={favicon(s.url)} alt="" className="size-3.5 rounded-sm" />
                {format(t('player.readOn'), { source: s.source })}
              </a>
            </li>
          ))}
        </ul>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" aria-label={t('player.like')} aria-pressed={vote === 'up'} onClick={() => onVote('up')}>
            <ThumbsUp className={cn(vote === 'up' && 'fill-primary text-primary')} />
          </Button>
          <Button variant="ghost" size="icon" aria-label={t('player.dislike')} aria-pressed={vote === 'down'} onClick={() => onVote('down')}>
            <ThumbsDown className={cn(vote === 'down' && 'fill-primary text-primary')} />
          </Button>
          {onSkip && (
            <Button variant="ghost" className="ml-auto" onClick={onSkip}>
              <SkipForward /> {t('player.skip')}
            </Button>
          )}
        </div>
      </div>
    </article>
  )
}
