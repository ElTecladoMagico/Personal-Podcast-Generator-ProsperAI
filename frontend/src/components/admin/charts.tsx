import type { ReactNode } from 'react'
import { Area, AreaChart, Bar, BarChart, CartesianGrid, ComposedChart, Line, XAxis, YAxis } from 'recharts'
import {
  type ChartConfig, ChartContainer, ChartLegend, ChartLegendContent, ChartTooltip, ChartTooltipContent,
} from '@/components/ui/chart'
import type { Cohort, Metrics } from '@/lib/admin'
import { pct } from '@/lib/admin'

const day = (d: string) => new Date(`${d}T00:00:00Z`).toLocaleDateString('en', { month: 'short', day: 'numeric', timeZone: 'UTC' })
const dayLabel = (label: ReactNode) => day(String(label))
const axis = { tickLine: false, axisLine: false, tickMargin: 8, fontSize: 12 } as const

const activity = {
  signups: { label: 'Sign-ups', color: 'var(--chart-2)' },
  dau: { label: 'DAU', color: 'var(--chart-1)' },
  wau: { label: 'WAU', color: 'var(--chart-3)' },
} satisfies ChartConfig

export function ActivityChart({ data }: { data: Metrics['growth']['daily'] }) {
  return (
    <ChartContainer config={activity} className="aspect-auto h-64 w-full">
      <ComposedChart data={data} margin={{ left: -16, right: 8 }}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="day" tickFormatter={day} minTickGap={24} {...axis} />
        <YAxis allowDecimals={false} {...axis} />
        <ChartTooltip content={<ChartTooltipContent labelFormatter={dayLabel} />} />
        <ChartLegend content={<ChartLegendContent />} />
        <Bar dataKey="signups" fill="var(--color-signups)" radius={2} />
        <Line dataKey="wau" stroke="var(--color-wau)" strokeWidth={2} dot={false} />
        <Line dataKey="dau" stroke="var(--color-dau)" strokeWidth={2} dot={false} />
      </ComposedChart>
    </ChartContainer>
  )
}

const episodes = {
  scheduled: { label: 'Scheduled', color: 'var(--chart-3)' },
  manual: { label: 'On demand', color: 'var(--chart-2)' },
  failed: { label: 'Failed', color: 'var(--chart-1)' },
} satisfies ChartConfig

export function EpisodesChart({ data }: { data: Metrics['operations']['daily'] }) {
  return (
    <ChartContainer config={episodes} className="aspect-auto h-56 w-full">
      <ComposedChart data={data} margin={{ left: -16, right: 8 }}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="day" tickFormatter={day} minTickGap={24} {...axis} />
        <YAxis allowDecimals={false} {...axis} />
        <ChartTooltip content={<ChartTooltipContent labelFormatter={dayLabel} />} />
        <ChartLegend content={<ChartLegendContent />} />
        <Bar dataKey="scheduled" stackId="e" fill="var(--color-scheduled)" />
        <Bar dataKey="manual" stackId="e" fill="var(--color-manual)" radius={[2, 2, 0, 0]} />
        <Line dataKey="failed" stroke="var(--color-failed)" strokeWidth={2} dot={false} />
      </ComposedChart>
    </ChartContainer>
  )
}

const cost = {
  tts_usd: { label: 'Voice (TTS)', color: 'var(--chart-1)' },
  llm_usd: { label: 'LLM', color: 'var(--chart-3)' },
} satisfies ChartConfig

export function CostChart({ data }: { data: Metrics['operations']['cost'] }) {
  return (
    <ChartContainer config={cost} className="aspect-auto h-56 w-full">
      <AreaChart data={data} margin={{ left: -8, right: 8 }}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="day" tickFormatter={day} minTickGap={24} {...axis} />
        <YAxis tickFormatter={(v: number) => `$${v.toFixed(1)}`} {...axis} />
        <ChartTooltip content={<ChartTooltipContent labelFormatter={dayLabel} />} />
        <ChartLegend content={<ChartLegendContent />} />
        <Area dataKey="llm_usd" stackId="c" type="monotone" fill="var(--color-llm_usd)" stroke="var(--color-llm_usd)" fillOpacity={0.5} />
        <Area dataKey="tts_usd" stackId="c" type="monotone" fill="var(--color-tts_usd)" stroke="var(--color-tts_usd)" fillOpacity={0.5} />
      </AreaChart>
    </ChartContainer>
  )
}

const completion = { listens: { label: 'Listens', color: 'var(--chart-1)' } } satisfies ChartConfig

export function CompletionChart({ data }: { data: Metrics['content']['completion'] }) {
  const rows = data.map((d) => ({ ...d, range: `${d.bucket * 10}–${d.bucket * 10 + 10}%` }))
  return (
    <ChartContainer config={completion} className="aspect-auto h-56 w-full">
      <BarChart data={rows} margin={{ left: -16, right: 8 }}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="range" interval={1} {...axis} />
        <YAxis allowDecimals={false} {...axis} />
        <ChartTooltip content={<ChartTooltipContent />} />
        <Bar dataKey="listens" fill="var(--color-listens)" radius={[2, 2, 0, 0]} />
      </BarChart>
    </ChartContainer>
  )
}

/** Cohort × week heat map: each cell is the share of that cohort active in that week. */
export function RetentionTable({ cohorts }: { cohorts: Cohort[] }) {
  const weeks = Math.max(0, ...cohorts.map((c) => c.weeks.length))
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs tabular-nums">
        <thead>
          <tr className="text-muted-foreground">
            <th className="py-1 pr-3 text-left font-normal">Signed up</th>
            <th className="px-1 text-right font-normal">Users</th>
            {Array.from({ length: weeks }, (_, w) => <th key={w} className="px-1 font-normal">W{w}</th>)}
          </tr>
        </thead>
        <tbody>
          {cohorts.map((c) => (
            <tr key={c.cohort}>
              <td className="py-0.5 pr-3 whitespace-nowrap">{day(c.cohort)}</td>
              <td className="px-1 text-right text-muted-foreground">{c.users}</td>
              {Array.from({ length: weeks }, (_, w) => {
                const v = c.weeks[w]
                return (
                  <td key={w} className="p-0.5">
                    {v != null && (
                      <span className="block rounded px-1 py-1 text-center"
                        style={{ background: `color-mix(in oklch, var(--chart-1) ${Math.round(v * 45) + 5}%, transparent)` }}>
                        {pct(v)}
                      </span>
                    )}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
