import { describe, expect, it } from 'vitest'
import { coverSeed, greetingKey, isTerminal, STAGES, stageStates } from './episodes'

describe('stageStates', () => {
  it('marks earlier stages done, the current one active and the rest pending', () => {
    const s = stageStates('writing', null)
    expect(s.queued).toBe('done')
    expect(s.researching).toBe('done')
    expect(s.writing).toBe('active')
    expect(s.verifying).toBe('pending')
  })
  it('shows where a failed episode broke', () => {
    const s = stageStates('failed', 'recording')
    expect(s.verifying).toBe('done')
    expect(s.recording).toBe('failed')
  })
  it('everything is done when ready', () => {
    expect(Object.values(stageStates('ready', null)).every((x) => x === 'done')).toBe(true)
  })
  it('covers the seven stages in order', () => {
    expect(STAGES).toEqual(['queued', 'fetching', 'editing', 'researching', 'writing', 'verifying', 'recording'])
  })
})

describe('isTerminal', () => {
  it('only ready and failed stop the polling', () => {
    expect([isTerminal('ready'), isTerminal('failed'), isTerminal('editing'), isTerminal(undefined)]).toEqual([
      true,
      true,
      false,
      false,
    ])
  })
})

describe('greetingKey', () => {
  it('follows the time of day', () => {
    expect([greetingKey(7), greetingKey(13), greetingKey(21), greetingKey(3)]).toEqual([
      'home.morning',
      'home.afternoon',
      'home.evening',
      'home.evening',
    ])
  })
})

describe('coverSeed', () => {
  it('is deterministic and spreads ids apart', () => {
    const a = coverSeed('3268378b-ee44-4dd0-8606-2a2d23923cbd')
    expect(a).toBe(coverSeed('3268378b-ee44-4dd0-8606-2a2d23923cbd'))
    expect(a).not.toBe(coverSeed('f2fe6140-149c-4cee-a8eb-d0cecf65cf75'))
    expect(a).toBeGreaterThanOrEqual(0)
  })
})
