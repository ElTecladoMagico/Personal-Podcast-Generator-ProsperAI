import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useApi } from './api'
import type { components } from './api-types'

export type EpisodeSummary = components['schemas']['EpisodeSummary']
export type EpisodeDetail = components['schemas']['EpisodeDetail']

// The pipeline's stages as the UI shows them (contract §6), plus the waiting room.
export const STAGES = ['queued', 'fetching', 'editing', 'researching', 'writing', 'verifying', 'recording'] as const
export type Stage = (typeof STAGES)[number]
export type StageState = 'done' | 'active' | 'pending' | 'failed'

export function isTerminal(status: string | undefined): boolean {
  return status === 'ready' || status === 'failed'
}

export function stageStates(status: string, failedStage: string | null | undefined): Record<Stage, StageState> {
  const current = status === 'failed' ? failedStage : status
  const at = status === 'ready' ? STAGES.length : STAGES.indexOf(current as Stage)
  return Object.fromEntries(
    STAGES.map((stage, i) => [
      stage,
      i < at ? 'done' : i > at ? 'pending' : status === 'failed' ? 'failed' : 'active',
    ]),
  ) as Record<Stage, StageState>
}

export function greetingKey(hour: number) {
  if (hour >= 6 && hour < 13) return 'home.morning' as const
  if (hour >= 13 && hour < 20) return 'home.afternoon' as const
  return 'home.evening' as const
}

/** FNV-1a: a stable number per episode, so its generative cover never changes. */
export function coverSeed(id: string): number {
  let hash = 0x811c9dc5
  for (const ch of id) {
    hash ^= ch.charCodeAt(0)
    hash = Math.imul(hash, 0x01000193)
  }
  return hash >>> 0
}

export function useEpisodes() {
  const request = useApi()
  return useQuery({ queryKey: ['episodes'], queryFn: () => request<EpisodeSummary[]>('/episodes') })
}

/** Polls every 1.5 s until the episode is ready or failed (ADR 0010: polling, not SSE). */
export function useEpisode(id: string | undefined) {
  const request = useApi()
  return useQuery({
    queryKey: ['episode', id],
    queryFn: () => request<EpisodeDetail>(`/episodes/${id}`),
    enabled: Boolean(id),
    refetchInterval: (q) => (isTerminal(q.state.data?.status) ? false : 1500),
  })
}

function useEpisodeAction(path: (id?: string) => string) {
  const request = useApi()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id?: string) => request<EpisodeDetail>(path(id), { method: 'POST' }),
    onSuccess: (episode) => {
      queryClient.setQueryData(['episode', episode.id], episode)
      queryClient.invalidateQueries({ queryKey: ['episodes'] })
    },
  })
}

export const useGenerate = () => useEpisodeAction(() => '/episodes')
export const useRetry = () => useEpisodeAction((id) => `/episodes/${id}/retry`)
