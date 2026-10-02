/** Pure helpers that map the audio clock to the script (chapters → turns → words). */
import type { components } from './api-types'

export type Script = components['schemas']['Script']
export type Chapter = components['schemas']['Chapter']
export type Turn = components['schemas']['Turn']

/** Index of the last item whose start is ≤ t (binary search), or -1. */
export function findActive(items: { start_s?: number | null }[], t: number): number {
  let lo = 0
  let hi = items.length - 1
  let found = -1
  while (lo <= hi) {
    const mid = (lo + hi) >> 1
    if ((items[mid].start_s ?? 0) <= t) {
      found = mid
      lo = mid + 1
    } else hi = mid - 1
  }
  return found
}

export type Position = { chapter: number; turn: number; word: number }

/** Chapter, turn and word being spoken at t. Gaps keep the previous turn highlighted. */
export function locate(script: Script, t: number): Position {
  const turns = script.chapters.flatMap((c, ci) => c.turns.map((turn, ti) => ({ ci, ti, start_s: turn.start_s })))
  const i = Math.max(findActive(turns, t), 0)
  const { ci, ti } = turns[i] ?? { ci: 0, ti: 0 }
  const words = script.chapters[ci]?.turns[ti]?.words
  const word = words ? findActive(words.map(([start_s]) => ({ start_s })), t) : -1
  return { chapter: ci, turn: ti, word }
}

export type Segment = { index: number; title: string; start: number; end: number; width: number }

/** The chapter bar: each chapter runs from its start to the next one's (the last to the end). */
export function chapterSegments(script: Script, duration: number): Segment[] {
  return script.chapters.map((c, i) => {
    const start = c.start_s ?? 0
    const end = script.chapters[i + 1]?.start_s ?? duration
    return { index: i, title: c.title, start, end, width: duration ? (100 * (end - start)) / duration : 0 }
  })
}

/** What the listener reads: audio tags like [laughs] are for the voices only. */
export function spokenText(text: string): string {
  return text.replace(/\[[a-z ]+\]/g, '').replace(/\s+/g, ' ').trim()
}

/** A forward seek across more than half of the chapter being played is a skip of that chapter. */
export function isSkip(script: Script, from: number, to: number): number | null {
  if (to <= from) return null
  const segs = chapterSegments(script, Infinity)
  const ci = findActive(segs.map((s) => ({ start_s: s.start })), from)
  const seg = segs[ci]
  if (!seg) return null
  const length = (script.chapters[ci].end_s ?? seg.end) - seg.start
  return to - from > length / 2 ? ci : null
}
