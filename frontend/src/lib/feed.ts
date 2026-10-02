import { useMutation, useQueryClient } from '@tanstack/react-query'
import { type Me, useApi } from './api'

/** Subscribe links: each app opens with the private feed already filled in. */
export function podcastApps(feedUrl: string) {
  const bare = feedUrl.replace(/^https?:\/\//, '')
  return [
    { name: 'Apple Podcasts', href: `podcast://${bare}` },
    { name: 'Overcast', href: `overcast://x-callback-url/add?url=${encodeURIComponent(feedUrl)}` },
    { name: 'Pocket Casts', href: `pktc://subscribe/${bare}` },
  ]
}

/** "sábado, 07:00" in the listener's own time zone, or null when it's on demand only. */
export function nextEpisodeLabel(at: string | null | undefined, timeZone: string, lang: string): string | null {
  if (!at) return null
  return new Date(at).toLocaleString(lang, { weekday: 'long', hour: '2-digit', minute: '2-digit', hourCycle: 'h23', timeZone })
}

export function useRotateFeedToken() {
  const request = useApi()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => request<Me>('/me/feed-token/rotate', { method: 'POST' }),
    onSuccess: (me) => queryClient.setQueryData(['me'], me),
  })
}
