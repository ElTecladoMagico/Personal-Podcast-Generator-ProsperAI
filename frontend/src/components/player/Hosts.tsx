import { useT } from '@/lib/i18n'
import { cn } from '@/lib/utils'
import { hostColor } from './hostColor'

/** The hosts as avatars; the one speaking gets a breathing ring while the audio plays. */
export function Hosts({ names, speaking, playing }: { names: string[]; speaking: number; playing: boolean }) {
  const { t } = useT()
  return (
    <ul className="flex gap-4">
      {names.map((name, i) => {
        const on = playing && i === speaking
        return (
          <li key={name} className="flex items-center gap-2">
            <span className="relative grid size-11 place-items-center rounded-full font-heading text-lg text-white"
              style={{ background: hostColor(i) }}>
              {on && <span className="absolute -inset-1 rounded-full border-2 motion-safe:animate-ping" style={{ borderColor: hostColor(i) }} />}
              {name[0]}
            </span>
            <span className={cn('text-sm transition-colors', on ? 'text-foreground' : 'text-muted-foreground')}>
              {name}
              {on && <span className="sr-only"> {t('player.speaking')}</span>}
            </span>
          </li>
        )
      })}
    </ul>
  )
}
