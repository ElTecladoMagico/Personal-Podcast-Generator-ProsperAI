import { useMutation } from '@tanstack/react-query'
import { useApi } from './api'
import type { components } from './api-types'

export type Answer = components['schemas']['AskOut']

/** Resume a little before the pause, so the listener catches the thread again. */
export const resumeAt = (pausedAt: number) => Math.max(0, pausedAt - 2)

/** The answer has no timings: follow it by each turn's share of the characters. */
export function activeTurn(turns: { text: string }[], time: number, duration: number): number {
  if (!duration) return 0
  const total = turns.reduce((n, t) => n + t.text.length, 0)
  let reached = 0
  for (const [i, t] of turns.entries()) {
    reached += t.text.length
    if (time < (reached / total) * duration) return i
  }
  return turns.length - 1
}

export function useAsk(episodeId: string) {
  const request = useApi()
  return useMutation({
    mutationFn: (body: { question: string; position_s: number }) =>
      request<Answer>(`/episodes/${episodeId}/ask`, { method: 'POST', body: JSON.stringify(body) }),
  })
}
