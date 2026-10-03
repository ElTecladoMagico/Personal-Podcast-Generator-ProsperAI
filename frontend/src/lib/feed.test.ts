import { describe, expect, it } from 'vitest'
import { nextEpisodeLabel, podcastApps } from './feed'

const FEED = 'https://api.podcast.scuda.es/feeds/abc_123.xml'

describe('podcastApps', () => {
  it('builds each app’s subscribe link from the feed URL', () => {
    expect(podcastApps(FEED)).toEqual([
      { name: 'Apple Podcasts', href: 'podcast://api.podcast.scuda.es/feeds/abc_123.xml' },
      { name: 'Pocket Casts', href: 'pktc://subscribe/api.podcast.scuda.es/feeds/abc_123.xml' },
    ])
  })
})

describe('nextEpisodeLabel', () => {
  const NOW = new Date('2026-10-03T00:30:00Z') // Saturday 02:30 in Madrid, Friday 20:30 in New York

  it('says today or tomorrow in the listener’s time zone', () => {
    expect(nextEpisodeLabel('2026-10-03T05:00:00Z', 'Europe/Madrid', 'es', NOW)).toBe('hoy, 07:00')
    expect(nextEpisodeLabel('2026-10-04T05:00:00Z', 'Europe/Madrid', 'es', NOW)).toBe('mañana, 07:00')
    expect(nextEpisodeLabel('2026-10-03T05:00:00Z', 'America/New_York', 'en', NOW)).toBe('tomorrow, 01:00')
  })

  it('uses the weekday further ahead', () => {
    expect(nextEpisodeLabel('2026-10-06T05:00:00Z', 'Europe/Madrid', 'es', NOW)).toBe('martes, 07:00')
  })

  it('is null when there is no schedule', () => {
    expect(nextEpisodeLabel(null, 'Europe/Madrid', 'es', NOW)).toBeNull()
  })
})
