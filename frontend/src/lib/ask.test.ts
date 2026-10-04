import { describe, expect, it } from 'vitest'
import { activeTurn, resumeAt } from './ask'

describe('resumeAt', () => {
  it('goes back 2 seconds so the listener catches the thread again', () => {
    expect(resumeAt(31.5)).toBe(29.5)
    expect(resumeAt(1)).toBe(0)
  })
})

describe('activeTurn', () => {
  const turns = [{ text: 'a'.repeat(100) }, { text: 'b'.repeat(300) }]

  it('follows the answer by its share of characters', () => {
    expect(activeTurn(turns, 0, 20)).toBe(0)
    expect(activeTurn(turns, 4.9, 20)).toBe(0) // first quarter of the audio = first turn
    expect(activeTurn(turns, 5.1, 20)).toBe(1)
    expect(activeTurn(turns, 20, 20)).toBe(1)
  })

  it('starts at the first turn before the audio duration is known', () => {
    expect(activeTurn(turns, 3, 0)).toBe(0)
  })
})
