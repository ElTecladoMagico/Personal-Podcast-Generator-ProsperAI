import { useMutation, useQueryClient } from '@tanstack/react-query'
import { type Me, useApi } from './api'

/** Subscribe links that open the app with the feed filled in (Apple Podcasts: Mac and iPhone;
 * Pocket Casts: phone). Any other app takes the copied URL ("Add by URL"). */
export function podcastApps(feedUrl: string) {
  const bare = feedUrl.replace(/^https?:\/\//, '')
  return [
    { name: 'Apple Podcasts', href: `podcast://${bare}` },
    { name: 'Pocket Casts', href: `pktc://subscribe/${bare}` },
  ]
}

/** "hoy, 07:00" / "mañana, 07:00" / "martes, 07:00" in the listener's time zone, or null when
 * it's on demand only. */
export function nextEpisodeLabel(
  at: string | null | undefined, timeZone: string, lang: string, now: Date = new Date(),
): string | null {
  if (!at) return null
  const when = new Date(at)
  const day = (d: Date) => Date.parse(d.toLocaleDateString('en-CA', { timeZone })) // local YYYY-MM-DD
  const daysAway = Math.round((day(when) - day(now)) / 86_400_000)
  const time = when.toLocaleTimeString(lang, { hour: '2-digit', minute: '2-digit', hourCycle: 'h23', timeZone })
  if (daysAway <= 1) return `${new Intl.RelativeTimeFormat(lang, { numeric: 'auto' }).format(daysAway, 'day')}, ${time}`
  return `${when.toLocaleDateString(lang, { weekday: 'long', timeZone })}, ${time}`
}

export function useRotateFeedToken() {
  const request = useApi()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => request<Me>('/me/feed-token/rotate', { method: 'POST' }),
    onSuccess: (me) => queryClient.setQueryData(['me'], me),
  })
}
