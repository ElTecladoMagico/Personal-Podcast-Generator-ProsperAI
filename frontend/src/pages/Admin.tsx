import { useState } from 'react'
import { ActivityChart, CompletionChart, CostChart, EpisodesChart, RetentionTable } from '@/components/admin/charts'
import { BarRow, Kpi, Panel, Stat } from '@/components/admin/parts'
import { Badge } from '@/components/ui/badge'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { Switch } from '@/components/ui/switch'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { funnelSteps, type Metrics, pct, RANGES, useAdminMetrics, usd } from '@/lib/admin'

// Internal tool: in English, for the team (and the reviewers). Definitions match backend/app/metrics.py.
const ACTIVE = 'Active = played, skipped, voted or downloaded an episode (web player or podcast app) that day, UTC.'
const FUNNEL_LABELS = {
  signed_up: 'Signed up',
  onboarded: 'Finished onboarding',
  first_episode: 'Got a first episode',
  listened_80: 'Listened to ≥ 80 %',
}

/** Is the product working? Growth, habit, content and operations, from the same events table. */
export default function Admin() {
  const [days, setDays] = useState<number>(30)
  const [includeMock, setIncludeMock] = useState(true)
  const { data, error, isFetching } = useAdminMetrics(days, includeMock)

  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-4xl sm:text-5xl">Is it working?</h1>
          <p className="text-muted-foreground">
            Usage metrics {data && `· ${data.range.first_day} → ${data.range.last_day} (UTC)`}
            {isFetching && ' · updating…'}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-4">
          <ToggleGroup type="single" variant="outline" value={String(days)} aria-label="Range"
            onValueChange={(v) => v && setDays(Number(v))}>
            {RANGES.map((r) => <ToggleGroupItem key={r} value={String(r)}>{r} days</ToggleGroupItem>)}
          </ToggleGroup>
          <div className="flex items-center gap-2">
            <Switch id="mock" checked={includeMock} onCheckedChange={setIncludeMock} />
            <Label htmlFor="mock">Simulated data</Label>
            <Badge variant={includeMock ? 'secondary' : 'outline'}>{includeMock ? 'Mocked + real' : 'Real only'}</Badge>
          </div>
        </div>
      </header>

      {error && <p className="text-destructive">{error.message}</p>}
      {!data ? <Skeleton className="h-96 w-full" /> : <Dashboard m={data} />}
    </div>
  )
}

function Dashboard({ m }: { m: Metrics }) {
  const { kpis, growth, content, operations: ops } = m
  const funnel = funnelSteps(growth.funnel)
  const maxStage = Math.max(1, ...ops.stages.map((s) => s.p95 ?? 0))
  const maxSkip = Math.max(0.01, ...content.skips_by_position.map((p) => p.skip_rate))
  const failures = ops.stages.reduce((n, s) => n + s.failures, 0)

  return (
    <>
      <section className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6" aria-label="Key metrics">
        <Kpi label="MAU" value={String(kpis.mau)} definition={`Distinct active listeners in the last 28 days. ${ACTIVE}`} />
        <Kpi label="DAU / MAU" value={pct(kpis.stickiness)} definition="Average daily active listeners over the last 28 days ÷ MAU. How much of the audience comes back every day: a daily show should aim high." />
        <Kpi label="Activation" value={pct(kpis.activation)} definition="Share of the listeners who signed up in the range and listened to ≥ 80 % of an episode within 48 h." />
        <Kpi label="Completion" value={pct(kpis.completion)} definition="Average of how far each listener got into each episode they played (furthest position ÷ duration)." />
        <Kpi label="👍 share" value={pct(kpis.thumbs_up)} definition="👍 ÷ (👍 + 👎) on story cards in the range." />
        <Kpi label="Cost / episode" value={usd(kpis.cost_per_episode)} definition="Average LLM cost plus voice characters × ElevenLabs price (Creator plan, 22 USD per 100k characters), for episodes made in the range." />
      </section>

      <h2 className="text-2xl">Growth and habit</h2>
      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Active listeners and sign-ups" className="lg:col-span-2"
          why="Sign-ups only matter if they turn into a habit: WAU should grow with them, not stay flat."
          definition={`DAU: active that day. WAU: active in the 7 days up to that day. ${ACTIVE}`}>
          <ActivityChart data={growth.daily} />
        </Panel>
        <Panel title="Activation funnel"
          why="Listening to the first episode is the moment that predicts retention: if they don't, they rarely come back."
          definition="Listeners who signed up in the range, and how many of them reached each step (at any time).">
          <ol className="space-y-2">
            {funnel.map((s) => (
              <BarRow key={s.step} label={FUNNEL_LABELS[s.step]} value={s.users} max={funnel[0].users}
                text={`${s.users} · ${pct(s.fromStart)}`} />
            ))}
          </ol>
          <p className="text-xs text-muted-foreground">
            Biggest drop: {biggestDrop(funnel)}
          </p>
        </Panel>
        <Panel title="Weekly retention by cohort"
          why="The habit test: a podcast people like keeps a flat tail instead of fading to zero."
          definition={`Listeners grouped by the week they signed up. Week N = days 7N to 7N+6 after their own sign-up; cell = share active at least once that week. ${ACTIVE}`}>
          <RetentionTable cohorts={growth.retention} />
        </Panel>
      </div>

      <h2 className="text-2xl">Content</h2>
      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="How far they listen"
          why="If most listens stop halfway, episodes are too long or the stories aren't the right ones."
          definition="One listen per listener and episode, by the furthest share of the episode they reached (web player only).">
          <CompletionChart data={content.completion} />
        </Panel>
        <Panel title="Skips by story position"
          why="Rising skips later in the episode mean the editor should put the strongest story first or make shorter shows."
          definition="Chapter skipped ÷ chapter started, by the story's position in the episode (1 = first story).">
          <ol className="space-y-2">
            {content.skips_by_position.map((p) => (
              <BarRow key={p.position} label={`Story ${p.position}`} value={p.skip_rate} max={maxSkip}
                text={`${pct(p.skip_rate)} of ${p.started}`} tone="signal" />
            ))}
          </ol>
        </Panel>
        <Panel title="Topics" className="lg:col-span-2"
          why="Which interests work: topics with many 👎 or skips need better sources or a different angle."
          definition="Stories told, grouped by the listener's interest they came from: plays (chapter started), 👍 share and skip rate.">
          <TopicTable topics={content.topics} />
        </Panel>
        <Panel title="Feature adoption" className="lg:col-span-2"
          why="Three bets of the product: delivery to podcast apps, setting it up in seconds by importing from your AI, and asking the hosts while listening."
          definition="Podcast app: share of active listeners with a feed download. Import: share of completed onboardings that used “Import from your AI”. Ask: share of active listeners who asked the hosts, and seconds until the answer is ready (p50 · p95).">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            <Stat label="Listen in a podcast app" value={pct(content.rss_adoption)} note="of active listeners" />
            <Stat label="Onboarded by importing" value={pct(content.import_share)} note="of finished onboardings" />
            <Stat label="Ask the hosts" value={pct(content.ask.askers_share)}
              note={`${content.ask.questions} questions · answer in ${fmtSeconds(content.ask.p50_latency_s)} · ${fmtSeconds(content.ask.p95_latency_s)}`} />
          </div>
        </Panel>
      </div>

      <h2 className="text-2xl">Operations</h2>
      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Episodes made"
          why="Scheduled episodes are the product working on its own; failures are listeners who got nothing that day."
          definition={`Episodes requested per day (UTC), by trigger, and how many failed. ${ops.requested} requested in the range, ${failures} failed (${pct(failures / Math.max(ops.requested, 1))}).`}>
          <EpisodesChart data={ops.daily} />
        </Panel>
        <Panel title="Cost per episode"
          why="The voice is most of the bill: length and TTS price drive the unit economics, not the LLM."
          definition="Daily average of the LLM cost and of voice characters × 22 USD per 100k (ElevenLabs Creator plan), for episodes that finished.">
          <CostChart data={ops.cost} />
        </Panel>
        <Panel title="Time and failures by stage"
          why="Where to invest: the slowest stage sets how early we must start, the most failing one is the next fix."
          definition="Seconds per stage for finished episodes (bar: p50, text: p50 · p95) and failed episodes by the stage they stopped at.">
          <ol className="space-y-2">
            {ops.stages.map((s) => (
              <BarRow key={s.stage} label={s.stage} value={s.p50 ?? 0} max={maxStage}
                text={`${fmtSeconds(s.p50)} · ${fmtSeconds(s.p95)}${s.failures ? ` · ${s.failures} failed` : ''}`} />
            ))}
          </ol>
        </Panel>
        <Panel title="Fact-checking"
          why="The checker is the product's promise of trust: every claim the sources don't support is fixed or cut before recording."
          definition="From finished episodes: how many had at least one flagged claim, and the flagged claims rewritten by the writer (the rest are removed).">
          <div className="grid grid-cols-3 gap-4">
            <Stat label="Episodes with issues" value={pct(ops.checker.with_issues / Math.max(ops.checker.episodes, 1))}
              note={`${ops.checker.with_issues} of ${ops.checker.episodes}`} />
            <Stat label="Claims flagged" value={String(ops.checker.issues_found)} note="unsupported or misattributed" />
            <Stat label="Fixed by rewriting" value={pct(ops.checker.issues_fixed / Math.max(ops.checker.issues_found, 1))}
              note="the rest were removed" />
          </div>
        </Panel>
      </div>
    </>
  )
}

function TopicTable({ topics }: { topics: Metrics['content']['topics'] }) {
  if (!topics.length) return <p className="text-sm text-muted-foreground">No stories played in this range yet.</p>
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm tabular-nums">
        <thead className="text-xs text-muted-foreground">
          <tr><th className="py-1 text-left font-normal">Topic</th><th className="text-right font-normal">Plays</th>
            <th className="text-right font-normal">👍 share</th><th className="text-right font-normal">Skip rate</th></tr>
        </thead>
        <tbody>
          {topics.map((t) => (
            <tr key={t.topic} className="border-t">
              <td className="py-1.5">{t.topic}</td>
              <td className="text-right">{t.plays}</td>
              <td className="text-right">{pct(t.thumbs_up)}</td>
              <td className="text-right">{pct(t.skip_rate)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function biggestDrop(funnel: ReturnType<typeof funnelSteps>) {
  const worst = funnel.slice(1).reduce((a, b) => ((b.fromPrevious ?? 1) < (a.fromPrevious ?? 1) ? b : a), funnel[1])
  return worst ? `${FUNNEL_LABELS[worst.step].toLowerCase()} (${pct(worst.fromPrevious)} of the step before)` : '—'
}

const fmtSeconds = (s: number | null) => (s == null ? '—' : `${s.toFixed(s < 10 ? 1 : 0)} s`)
