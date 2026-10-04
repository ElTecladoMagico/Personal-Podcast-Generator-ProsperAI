import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useApi } from './api'

// Shape of GET /admin/metrics (backend/app/metrics.py). Typed here because the endpoint
// returns a plain dict: one internal page reads it.
export type Day = { day: string; dau: number; wau: number; signups: number }
export type FunnelStep = { step: 'signed_up' | 'onboarded' | 'first_episode' | 'listened_80'; users: number }
export type Cohort = { cohort: string; users: number; weeks: number[] }
export type Topic = { topic: string; plays: number; skips: number; ups: number; downs: number; thumbs_up: number | null; skip_rate: number | null }
export type Stage = { stage: string; p50: number | null; p95: number | null; failures: number }
export type Metrics = {
  range: { first_day: string; last_day: string; days: number }
  include_mock: boolean
  kpis: {
    mau: number
    stickiness: number | null
    activation: number | null
    completion: number | null
    thumbs_up: number | null
    cost_per_episode: number | null
  }
  growth: { daily: Day[]; funnel: FunnelStep[]; retention: Cohort[] }
  content: {
    completion: { bucket: number; listens: number }[]
    skips_by_position: { position: number; started: number; skipped: number; skip_rate: number }[]
    topics: Topic[]
    rss_adoption: number | null
    import_share: number | null
    ask: { questions: number; askers_share: number | null; p50_latency_s: number | null; p95_latency_s: number | null }
  }
  operations: {
    daily: { day: string; manual: number; scheduled: number; failed: number }[]
    requested: number
    stages: Stage[]
    cost: { day: string; llm_usd: number; tts_usd: number }[]
    checker: { episodes: number; with_issues: number; issues_found: number; issues_fixed: number }
  }
}

export const RANGES = [7, 30, 90] as const

export function useAdminMetrics(days: number, includeMock: boolean) {
  const request = useApi()
  return useQuery({
    queryKey: ['admin-metrics', days, includeMock],
    queryFn: () => request<Metrics>(`/admin/metrics?days=${days}&include_mock=${includeMock}`),
    placeholderData: keepPreviousData, // keep the charts on screen while another range loads
  })
}

const share = (part: number, whole: number) => (whole ? part / whole : null)

/** Each funnel step with its conversion from the step before and from the first one. */
export function funnelSteps(funnel: FunnelStep[]) {
  return funnel.map((s, i) => ({
    ...s,
    fromPrevious: i === 0 ? share(s.users, s.users) : share(s.users, funnel[i - 1].users),
    fromStart: share(s.users, funnel[0].users),
  }))
}

export const pct = (v: number | null | undefined) => (v == null ? '—' : `${Math.round(v * 100)}%`)
export const usd = (v: number | null | undefined) => (v == null ? '—' : `$${v.toFixed(2)}`)
