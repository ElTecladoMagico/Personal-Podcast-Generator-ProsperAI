import { Info } from 'lucide-react'
import type { ReactNode } from 'react'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'

/** The definition behind a number, one tap away. */
export function Definition({ children }: { children: ReactNode }) {
  return (
    <Tooltip>
      <TooltipTrigger className="text-muted-foreground hover:text-foreground" aria-label="Definition">
        <Info className="size-3.5" />
      </TooltipTrigger>
      <TooltipContent className="max-w-72">{children}</TooltipContent>
    </Tooltip>
  )
}

/** One chart or table: what it is, why it matters for the product, and how it's computed. */
export function Panel({ title, why, definition, children, className }: {
  title: string
  why: string
  definition: string
  children: ReactNode
  className?: string
}) {
  return (
    <section className={cn('space-y-3 rounded-2xl border bg-card p-5', className)}>
      <header className="space-y-1">
        <h3 className="flex items-center gap-1.5 font-medium">{title} <Definition>{definition}</Definition></h3>
        <p className="text-sm text-muted-foreground">{why}</p>
      </header>
      {children}
    </section>
  )
}

export function Kpi({ label, value, definition }: { label: string; value: string; definition: string }) {
  return (
    <div className="space-y-1 rounded-2xl border bg-card p-4">
      <p className="flex items-center gap-1.5 text-xs tracking-wide text-muted-foreground uppercase">
        {label} <Definition>{definition}</Definition>
      </p>
      <p className="font-heading text-4xl tabular-nums">{value}</p>
    </div>
  )
}

/** A labelled horizontal bar: readable on any screen and with no chart library. */
export function BarRow({ label, value, max, text, tone = 'primary' }: {
  label: string
  value: number
  max: number
  text: string
  tone?: 'primary' | 'signal'
}) {
  return (
    <li className="grid grid-cols-[minmax(0,9rem)_1fr_auto] items-center gap-3 text-sm">
      <span className="truncate" title={label}>{label}</span>
      <span className="h-2 overflow-hidden rounded-full bg-muted" aria-hidden>
        <span className={cn('block h-full rounded-full', tone === 'primary' ? 'bg-primary' : 'bg-signal')}
          style={{ width: `${max ? (value / max) * 100 : 0}%` }} />
      </span>
      <span className="text-right text-muted-foreground tabular-nums">{text}</span>
    </li>
  )
}

export function Stat({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <div className="space-y-0.5">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="font-heading text-3xl tabular-nums">{value}</p>
      <p className="text-xs text-muted-foreground">{note}</p>
    </div>
  )
}
