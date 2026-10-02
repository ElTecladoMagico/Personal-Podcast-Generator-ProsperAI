import { describe, expect, it } from 'vitest'
import { chapterSegments, findActive, isSkip, locate, spokenText, type Script } from './timeline'

const script: Script = {
  title: 'T',
  summary: 'S',
  chapters: [
    { story_id: null, title: 'Intro', start_s: 0, end_s: 10, turns: [
      { speaker: 0, text: '[excited] Hola Pedro', source_ids: [], start_s: 0, end_s: 4, words: [[0, 'Hola'], [0.6, 'Pedro']] },
      { speaker: 1, text: 'Buenos días', source_ids: [], start_s: 4.2, end_s: 10, words: null },
    ] },
    { story_id: 's1', title: 'Chips', start_s: 10.5, end_s: 60, turns: [
      { speaker: 0, text: 'Nvidia', source_ids: ['a1'], start_s: 10.5, end_s: 60, words: [[10.5, 'Nvidia']] },
    ] },
  ],
}

describe('findActive', () => {
  const items = [{ start_s: 0 }, { start_s: 5 }, { start_s: 9 }]
  it('returns the last item that started at or before t', () => {
    expect([findActive(items, 0), findActive(items, 4.9), findActive(items, 5), findActive(items, 100)]).toEqual([0, 0, 1, 2])
  })
  it('is -1 before the first item or for an empty list', () => {
    expect([findActive(items, -1), findActive([], 3)]).toEqual([-1, -1])
  })
})

describe('locate', () => {
  it('finds chapter, turn and word at a time', () => {
    expect(locate(script, 0.7)).toEqual({ chapter: 0, turn: 0, word: 1 })
    expect(locate(script, 5)).toEqual({ chapter: 0, turn: 1, word: -1 })  // turn without words
    expect(locate(script, 30)).toEqual({ chapter: 1, turn: 0, word: 0 })
  })
  it('keeps the previous turn during the gap between chapters', () => {
    expect(locate(script, 10.2)).toEqual({ chapter: 0, turn: 1, word: -1 })
  })
})

describe('chapterSegments', () => {
  it('splits the bar by chapter start, the last one running to the end', () => {
    const segs = chapterSegments(script, 60)
    expect(segs.map((s) => [s.start, s.end])).toEqual([[0, 10.5], [10.5, 60]])
    expect(segs[0].width + segs[1].width).toBeCloseTo(100)
  })
})

describe('spokenText', () => {
  it('drops audio tags', () => {
    expect(spokenText('[excited] Hola [laughs] Pedro')).toBe('Hola Pedro')
  })
})

describe('isSkip', () => {
  it('a forward seek over more than half of the current chapter counts as a skip', () => {
    expect(isSkip(script, 12, 40)).toBe(1)  // 28 s of a 49.5 s chapter
    expect(isSkip(script, 12, 20)).toBe(null)  // small jump
    expect(isSkip(script, 40, 12)).toBe(null)  // backwards
  })
})
