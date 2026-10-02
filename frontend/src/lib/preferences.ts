import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { type Me, useApi } from './api'
import type { components } from './api-types'
import type { Lang } from './i18n'

export type Preferences = components['schemas']['Preferences']
export type Interest = components['schemas']['Interest']
export type Host = components['schemas']['Host']
export type Voice = components['schemas']['Voice']
export type ImportedPreferences = components['schemas']['ImportedPreferences']
export type Format = Preferences['format']

const MAX_INTERESTS = 12

export function newPreferences(language: string, timezone: string, voices: Voice[]): Preferences {
  return {
    interests: [],
    avoid: [],
    sources_i_trust: [],
    language,
    tone: 'casual',
    depth: 'analysis',
    format: 'duo',
    duration_min: 10,
    hosts: defaultHosts(voices, language),
    schedule: { frequency: 'daily', time: '07:00', weekday: null, timezone },
  }
}

export function addInterest(list: Interest[], topic: string): Interest[] {
  const clean = topic.trim().slice(0, 80)
  const known = list.some((i) => i.topic.toLowerCase() === clean.toLowerCase())
  if (!clean || known || list.length >= MAX_INTERESTS) return list
  return [...list, { topic: clean, why: null, weight: 3 }]
}

/** What the user's AI answered, on top of what they already chose (theirs wins on duplicates). */
export function mergeImported(draft: Preferences, imported: ImportedPreferences): Preferences {
  let interests = draft.interests
  for (const i of imported.interests) {
    const next = addInterest(interests, i.topic)
    if (next !== interests) next[next.length - 1] = { topic: next[next.length - 1].topic, why: i.why ?? null, weight: i.weight ?? 3 }
    interests = next
  }
  return {
    ...draft,
    interests,
    avoid: [...new Set([...(draft.avoid ?? []), ...(imported.avoid ?? [])])],
    sources_i_trust: [...new Set([...(draft.sources_i_trust ?? []), ...(imported.sources_i_trust ?? [])])],
    language: imported.language ?? draft.language,
    tone: imported.tone ?? draft.tone,
    depth: imported.depth ?? draft.depth,
  }
}

/** A female + male pair that sounds native in the podcast language (English otherwise). */
export function defaultHosts(voices: Voice[], language: string): Host[] {
  const native = voices.some((v) => v.language === language) ? language : 'en'
  const pick = (gender: Voice['gender']) => voices.find((v) => v.language === native && v.gender === gender)
  return [pick('female'), pick('male')].filter((v) => v !== undefined).map((v) => ({ name: v.name, voice_id: v.id }))
}

export function hostsForFormat(format: Format, hosts: Host[], voices: Voice[], language: string): Host[] {
  const wanted = format === 'solo' ? 1 : 2
  if (hosts.length === wanted) return hosts
  if (hosts.length > wanted) return hosts.slice(0, wanted)
  const extra = defaultHosts(voices, language).find((h) => !hosts.some((x) => x.voice_id === h.voice_id))
  return extra ? [...hosts, extra] : hosts
}

// --- "Import from your AI" (ADR 0012): works in ChatGPT, Claude or Gemini, memory or not ---

export const IMPORT_PROMPT: Record<Lang, string> = {
  en: `I'm setting up a personal daily news podcast. Using everything you know about me (memory, past conversations), describe my interests. If you don't know enough, ask me up to 3 quick questions first, then answer.
Reply with ONLY this JSON, no extra text:
{"interests":[{"topic":"<specific topic, e.g. 'EU AI regulation' not 'tech'>","why":"<one line>","weight":<1-5>}],
 "avoid":["<topics I dislike>"],
 "sources_i_trust":["<outlets>"],
 "language":"<ISO 639-1 of the language I speak with you>",
 "tone":"casual|serious|nerdy",
 "depth":"headlines|analysis"}
Give 5-10 interests, as specific as possible.`,
  es: `Estoy configurando un podcast diario de noticias personalizado. Con todo lo que sabes de mí (memoria, conversaciones anteriores), describe mis intereses. Si no sabes lo suficiente, hazme antes hasta 3 preguntas rápidas y luego responde.
Responde SOLO con este JSON, sin texto adicional:
{"interests":[{"topic":"<tema concreto, p. ej. 'regulación europea de la IA', no 'tecnología'>","why":"<una línea>","weight":<1-5>}],
 "avoid":["<temas que no me gustan>"],
 "sources_i_trust":["<medios>"],
 "language":"<código ISO 639-1 del idioma en el que hablo contigo>",
 "tone":"casual|serious|nerdy",
 "depth":"headlines|analysis"}
Dame entre 5 y 10 intereses, lo más concretos posible.`,
}

export const SUGGESTIONS: Record<Lang, Record<string, string[]>> = {
  en: {
    Technology: ['Artificial intelligence', 'Startups and venture capital', 'Cybersecurity', 'Apple and Google'],
    Economy: ['Housing market', 'Inflation and interest rates', 'Personal finance', 'Stock markets'],
    Sports: ['Formula 1', 'Champions League', 'NBA', 'Tennis'],
    Science: ['Space exploration', 'Climate science', 'Medicine breakthroughs'],
    Culture: ['Movies and series', 'Music', 'Books'],
    Politics: ['European Union', 'US politics', 'Geopolitics'],
  },
  es: {
    Tecnología: ['Inteligencia artificial', 'Startups e inversión', 'Ciberseguridad', 'Apple y Google'],
    Economía: ['Vivienda en España', 'Inflación y tipos de interés', 'Finanzas personales', 'Bolsa'],
    Deportes: ['Fórmula 1', 'LaLiga', 'Champions League', 'Tenis'],
    Ciencia: ['Espacio', 'Cambio climático', 'Avances en medicina'],
    Cultura: ['Cine y series', 'Música', 'Libros'],
    Política: ['Política española', 'Unión Europea', 'Geopolítica'],
  },
}

export const LANGUAGES = [
  { code: 'es', label: 'Español' },
  { code: 'en', label: 'English' },
  { code: 'fr', label: 'Français' },
  { code: 'de', label: 'Deutsch' },
  { code: 'it', label: 'Italiano' },
  { code: 'pt', label: 'Português' },
]

// --- API ---------------------------------------------------------------------------

export function useVoices() {
  const request = useApi()
  return useQuery({ queryKey: ['voices'], queryFn: () => request<Voice[]>('/voices'), staleTime: Infinity })
}

export function useImportPreferences() {
  const request = useApi()
  return useMutation({
    mutationFn: (text: string) =>
      request<ImportedPreferences>('/me/preferences/import', { method: 'POST', body: JSON.stringify({ text }) }),
  })
}

export function useSavePreferences() {
  const request = useApi()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: { preferences: Preferences; method: 'import' | 'manual' }) =>
      request<Me>('/me/preferences', { method: 'PUT', body: JSON.stringify(body) }),
    onSuccess: (me) => queryClient.setQueryData(['me'], me),
  })
}
