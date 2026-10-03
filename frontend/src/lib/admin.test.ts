import { describe, expect, it } from 'vitest'
import { funnelSteps, pct, usd } from './admin'

describe('funnelSteps', () => {
  it('adds the conversion from the previous step and from the start', () => {
    const steps = funnelSteps([
      { step: 'signed_up', users: 200 },
      { step: 'onboarded', users: 160 },
      { step: 'first_episode', users: 150 },
      { step: 'listened_80', users: 60 },
    ])
    expect(steps.map((s) => [s.fromPrevious, s.fromStart])).toEqual([[1, 1], [0.8, 0.8], [0.9375, 0.75], [0.4, 0.3]])
  })

  it('does not divide by zero when nobody signed up', () => {
    expect(funnelSteps([{ step: 'signed_up', users: 0 }, { step: 'onboarded', users: 0 }])[1].fromStart).toBeNull()
  })
})

describe('formatting', () => {
  it('shows a dash when there is no data yet', () => {
    expect([pct(0.256), pct(null), usd(1.5326), usd(null)]).toEqual(['26%', '—', '$1.53', '—'])
  })
})
