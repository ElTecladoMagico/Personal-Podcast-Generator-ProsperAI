import { Pause, Play, RotateCcw, RotateCw } from 'lucide-react'
import type { ReactNode } from 'react'
import { Button } from '@/components/ui/button'
import { useT } from '@/lib/i18n'

const RATES = [0.8, 1, 1.25, 1.5, 2]
const clock = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`

export function Controls({ playing, time, duration, rate, onToggle, onSeek, onRate, disabled, children }: {
  playing: boolean
  time: number
  duration: number
  rate: number
  onToggle: () => void
  onSeek: (t: number) => void
  onRate: (r: number) => void
  disabled?: boolean
  children?: ReactNode // extra actions at the end of the row
}) {
  const { t } = useT()
  return (
    <div className="flex items-center gap-2">
      <Button variant="ghost" size="icon" aria-label={t('player.back')} onClick={() => onSeek(time - 15)} disabled={disabled}>
        <RotateCcw />
      </Button>
      <Button size="icon" className="size-14 rounded-full" aria-label={playing ? t('player.pause') : t('player.play')} onClick={onToggle} disabled={disabled}>
        {playing ? <Pause className="size-6" /> : <Play className="size-6 translate-x-px" />}
      </Button>
      <Button variant="ghost" size="icon" aria-label={t('player.forward')} onClick={() => onSeek(time + 30)} disabled={disabled}>
        <RotateCw />
      </Button>
      <span className="ml-2 text-sm text-muted-foreground tabular-nums">
        {clock(time)} / {clock(duration)}
      </span>
      <Button variant="ghost" size="sm" className="ml-auto tabular-nums" aria-label={`${rate}× · ${t('player.speed')}`} disabled={disabled}
        onClick={() => onRate(RATES[(RATES.indexOf(rate) + 1) % RATES.length])}>
        {rate}×
      </Button>
      {children}
    </div>
  )
}
