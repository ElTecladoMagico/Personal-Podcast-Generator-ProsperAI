import { createContext, use, useEffect, useState, type ReactNode } from 'react'

// UI language only; the podcast language is a separate user preference.
const en = {
  'nav.home': 'Home',
  'nav.settings': 'Settings',
  'nav.admin': 'Admin',
  'nav.language': 'Language',
  'nav.theme': 'Toggle theme',
  'auth.signIn': 'Sign in',
  'auth.getStarted': 'Get started',
  'landing.onAir': 'On air',
  'landing.title1': 'Your news,',
  'landing.title2': 'as a podcast',
  'landing.title3': 'made for you.',
  'landing.subtitle':
    'Tell us what you care about. Every morning, two hosts read the news for you, check the facts and turn it into a show worth listening to.',
  'landing.benefit1.title': 'Made for you',
  'landing.benefit1.body':
    'Your interests, your language, your hosts. It remembers what you heard and follows up on stories.',
  'landing.benefit2.title': 'Arrives on its own',
  'landing.benefit2.body':
    'A fresh episode on your schedule, in the web player or your favorite podcast app via a private feed.',
  'landing.benefit3.title': 'Ask the hosts',
  'landing.benefit3.body':
    'Something unclear? Pause, ask a question and the hosts answer you out loud, with sources.',
  'page.home': 'Your episodes',
  'page.onboarding': 'Set up your show',
  'page.episode': 'Episode',
  'page.settings': 'Settings',
  'page.admin': 'Usage metrics',
  'page.notFound': 'Nothing on this frequency',
  'page.notFoundBody': 'The page you are looking for does not exist.',
  'page.backHome': 'Back home',
  'error.generic': 'Something went wrong',
  'home.hello': 'Hello',
}

type Key = keyof typeof en

const es: Record<Key, string> = {
  'nav.home': 'Inicio',
  'nav.settings': 'Ajustes',
  'nav.admin': 'Admin',
  'nav.language': 'Idioma',
  'nav.theme': 'Cambiar tema',
  'auth.signIn': 'Entrar',
  'auth.getStarted': 'Empezar',
  'landing.onAir': 'En antena',
  'landing.title1': 'Tus noticias,',
  'landing.title2': 'en un podcast',
  'landing.title3': 'hecho para ti.',
  'landing.subtitle':
    'Cuéntanos qué te interesa. Cada mañana, dos presentadores leen las noticias por ti, comprueban los hechos y las convierten en un programa que apetece escuchar.',
  'landing.benefit1.title': 'Hecho para ti',
  'landing.benefit1.body':
    'Tus temas, tu idioma, tus presentadores. Recuerda lo que ya escuchaste y hace seguimiento de las historias.',
  'landing.benefit2.title': 'Llega solo',
  'landing.benefit2.body':
    'Un episodio nuevo a la hora que elijas, en el reproductor web o en tu app de podcasts con un feed privado.',
  'landing.benefit3.title': 'Pregunta a los presentadores',
  'landing.benefit3.body':
    '¿Algo no quedó claro? Pausa, pregunta y te responden en voz alta, con fuentes.',
  'page.home': 'Tus episodios',
  'page.onboarding': 'Configura tu programa',
  'page.episode': 'Episodio',
  'page.settings': 'Ajustes',
  'page.admin': 'Métricas de uso',
  'page.notFound': 'Nada en esta frecuencia',
  'page.notFoundBody': 'La página que buscas no existe.',
  'page.backHome': 'Volver al inicio',
  'error.generic': 'Algo ha fallado',
  'home.hello': 'Hola',
}

export const messages = { en, es }
export type Lang = keyof typeof messages
const STORAGE_KEY = 'ui-lang'

export function detectLang(stored: string | null, browser: string): Lang {
  if (stored === 'en' || stored === 'es') return stored
  return browser.toLowerCase().startsWith('es') ? 'es' : 'en'
}

function readStored(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY)
  } catch {
    return null // storage blocked (private mode)
  }
}

type I18n = { lang: Lang; setLang: (lang: Lang) => void; t: (key: Key) => string }
const I18nContext = createContext<I18n | null>(null)

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState(() => detectLang(readStored(), navigator.language))
  const setLang = (next: Lang) => {
    setLangState(next)
    try {
      localStorage.setItem(STORAGE_KEY, next)
    } catch {
      // not persisted; fine
    }
  }
  useEffect(() => {
    document.documentElement.lang = lang
  }, [lang])
  const t = (key: Key) => messages[lang][key]
  return <I18nContext value={{ lang, setLang, t }}>{children}</I18nContext>
}

export function useT(): I18n {
  const ctx = use(I18nContext)
  if (!ctx) throw new Error('useT must be used inside <I18nProvider>')
  return ctx
}
