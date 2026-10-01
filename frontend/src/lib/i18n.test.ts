import { describe, expect, it } from 'vitest'
import { detectLang, messages } from './i18n'

describe('detectLang', () => {
  it('prefers the stored choice', () => {
    expect(detectLang('es', 'en-US')).toBe('es')
  })
  it('falls back to the browser language', () => {
    expect(detectLang(null, 'es-ES')).toBe('es')
  })
  it('uses English for unsupported languages or junk in storage', () => {
    expect(detectLang('xx', 'fr-FR')).toBe('en')
  })
})

describe('messages', () => {
  it('Spanish has every English key', () => {
    expect(Object.keys(messages.es).sort()).toEqual(Object.keys(messages.en).sort())
  })
})
