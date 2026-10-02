import { describe, expect, it } from 'vitest'
import { nextEpisodeLabel, podcastApps } from './feed'

const FEED = 'https://api.podcast.scuda.es/feeds/abc_123.xml'

describe('podcastApps', () => {
  it('builds each app’s subscribe link from the feed URL', () => {
    expect(podcastApps(FEED)).toEqual([
      { name: 'Apple Podcasts', href: 'podcast://api.podcast.scuda.es/feeds/abc_123.xml' },
      { name: 'Overcast', href: `overcast://x-callback-url/add?url=${encodeURIComponent(FEED)}` },
      { name: 'Pocket Casts', href: 'pktc://subscribe/api.podcast.scuda.es/feeds/abc_123.xml' },
    ])
  })
})

describe('nextEpisodeLabel', () => {
  it('shows the weekday and time in the listener’s time zone', () => {
    expect(nextEpisodeLabel('2026-10-03T05:00:00Z', 'Europe/Madrid', 'es')).toBe('sábado, 07:00')
    expect(nextEpisodeLabel('2026-10-03T05:00:00Z', 'America/New_York', 'en')).toBe('Saturday 01:00')
  })

  it('is null when there is no schedule', () => {
    expect(nextEpisodeLabel(null, 'Europe/Madrid', 'es')).toBeNull()
  })
})
