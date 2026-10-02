import { describe, expect, it } from 'vitest'
import { addInterest, defaultHosts, hostsForFormat, mergeImported, newPreferences, type Voice } from './preferences'

const voice = (id: string, name: string, language: 'es' | 'en', gender: 'female' | 'male'): Voice => ({
  id,
  name,
  language,
  gender,
  descriptor: { en: '', es: '' },
  preview: `/voices/${id}.mp3`,
})
const VOICES = [
  voice('sara', 'Sara', 'es', 'female'),
  voice('martin', 'Martín', 'es', 'male'),
  voice('sarah', 'Sarah', 'en', 'female'),
  voice('george', 'George', 'en', 'male'),
]

describe('addInterest', () => {
  it('trims, ignores duplicates (any case) and stops at 12', () => {
    let list = addInterest([], '  Fórmula 1 ')
    list = addInterest(list, 'fórmula 1')
    expect(list).toEqual([{ topic: 'Fórmula 1', why: null, weight: 3 }])
    for (let i = 0; i < 20; i++) list = addInterest(list, `t${i}`)
    expect(list).toHaveLength(12)
    expect(addInterest(list, '   ')).toBe(list)
  })
})

describe('mergeImported', () => {
  it('adds new interests, keeps existing ones and takes the style the AI suggested', () => {
    const draft = { ...newPreferences('es', 'Europe/Madrid', VOICES), interests: [{ topic: 'IA', why: null, weight: 5 }] }
    const merged = mergeImported(draft, {
      interests: [{ topic: 'ia', why: 'dup', weight: 1 }, { topic: 'Vivienda', why: 'piso', weight: 4 }],
      avoid: ['fútbol'],
      sources_i_trust: [],
      language: null,
      tone: 'nerdy',
      depth: null,
    })
    expect(merged.interests.map((i) => [i.topic, i.weight])).toEqual([['IA', 5], ['Vivienda', 4]])
    expect(merged.avoid).toEqual(['fútbol'])
    expect([merged.tone, merged.depth, merged.language]).toEqual(['nerdy', 'analysis', 'es'])
  })
})

describe('hosts', () => {
  it('defaults to a female + male pair that sounds native in the podcast language', () => {
    expect(defaultHosts(VOICES, 'es').map((h) => h.voice_id)).toEqual(['sara', 'martin'])
    expect(defaultHosts(VOICES, 'fr').map((h) => h.voice_id)).toEqual(['sarah', 'george'])
  })
  it('solo keeps one host, duo and debate need two', () => {
    const two = defaultHosts(VOICES, 'es')
    expect(hostsForFormat('solo', two, VOICES, 'es')).toEqual([two[0]])
    expect(hostsForFormat('duo', [two[0]], VOICES, 'es')).toEqual(two)
    expect(hostsForFormat('debate', two, VOICES, 'es')).toBe(two)
  })
})
