import { useMutation, useQueryClient } from '@tanstack/react-query'
import { type Me, useApi } from './api'

/** Subscribe links that open the app with the feed filled in (Apple Podcasts: Mac and iPhone;
 * Pocket Casts: phone). Any other
 * app takes the copied URL ("Add by URL"). */
export function podcastApps(feedUrl: string) {
  const bare = feedUrl.replace(/^https?:\/\//, '')
  return [
    { name: 'Apple Podcasts', href: `podcast://${bare}` },
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
