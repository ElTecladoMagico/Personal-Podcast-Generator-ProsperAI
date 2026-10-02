import { useCallback, useEffect, useRef, useState } from 'react'

/** A small hand-rolled audio player around an <audio> element the page renders with `ref`.
 *  The clock is read every animation frame while playing, which keeps word highlighting
 *  smooth (timeupdate only fires ~4 times a second). */
export function useAudio() {
  const ref = useRef<HTMLAudioElement>(null)
  const [playing, setPlaying] = useState(false)
  const [time, setTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [rate, setRateState] = useState(1)

  useEffect(() => {
    const audio = ref.current
    if (!audio) return
    const onMeta = () => setDuration(audio.duration)
    const onPlay = () => setPlaying(true)
    const onPause = () => setPlaying(false)
    audio.addEventListener('loadedmetadata', onMeta)
    audio.addEventListener('play', onPlay)
    audio.addEventListener('pause', onPause)
    audio.addEventListener('ended', onPause)
    return () => {
      audio.removeEventListener('loadedmetadata', onMeta)
      audio.removeEventListener('play', onPlay)
      audio.removeEventListener('pause', onPause)
      audio.removeEventListener('ended', onPause)
    }
  }, [])

  useEffect(() => {
    if (!playing) return
    let frame = requestAnimationFrame(function tick() {
      setTime(ref.current?.currentTime ?? 0)
      frame = requestAnimationFrame(tick)
    })
    return () => cancelAnimationFrame(frame)
  }, [playing])

  const toggle = useCallback(() => {
    const audio = ref.current
    if (!audio) return
    if (audio.paused) void audio.play()
    else audio.pause()
  }, [])
  const seek = useCallback((t: number) => {
    const audio = ref.current
    if (!audio) return
    audio.currentTime = Math.min(Math.max(t, 0), audio.duration || t)
    setTime(audio.currentTime)
  }, [])
  const setRate = useCallback((r: number) => {
    if (ref.current) ref.current.playbackRate = r
    setRateState(r)
  }, [])
  return { ref, playing, time, duration, rate, toggle, seek, setRate }
}
