import { useCallback, useEffect, useRef } from 'react'
import { useApi } from './api'

type EventType = 'play_started' | 'chapter_started' | 'chapter_skipped' | 'listen_progress' | 'feedback'

/** Listening events (contract §8): they tune the editor and feed the dashboard. Fire and forget. */
export function useTrack(episodeId: string, duration: number) {
  const request = useApi()
  const maxPosition = useRef(0)

  const track = useCallback(
    (type: EventType, props: Record<string, unknown> = {}) =>
      request('/events', {
        method: 'POST',
        keepalive: true, // still delivered when the tab is closing
        body: JSON.stringify({ type, episode_id: episodeId, props }),
      }).catch(() => {}),
    [request, episodeId],
  )
  const progress = useCallback(
    () => maxPosition.current > 0 && track('listen_progress', { max_position_s: Math.round(maxPosition.current), duration_s: Math.round(duration) }),
    [track, duration],
  )

  useEffect(() => {
    const onHide = () => document.visibilityState === 'hidden' && progress()
    document.addEventListener('visibilitychange', onHide)
    const every = window.setInterval(progress, 60_000)
    return () => {
      document.removeEventListener('visibilitychange', onHide)
      window.clearInterval(every)
    }
  }, [progress])

  const seen = useCallback((t: number) => {
    maxPosition.current = Math.max(maxPosition.current, t)
  }, [])
  return { track, progress, seen }
}
