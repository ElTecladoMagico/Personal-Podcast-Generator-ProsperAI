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
  'landing.demo.date': 'Tuesday briefing',
  'landing.demo.title': 'Chips, chatbots and a late winner',
  'landing.demo.ch1': 'Good morning, Ana',
  'landing.demo.ch2': 'Europe’s AI rules start to bite',
  'landing.demo.ch3': 'The new chip everyone is waiting for',
  'landing.demo.ch4': 'Last night’s match, in two minutes',
  'landing.demo.hosts': 'with Sara & Martín',
  'landing.footer': 'Built for the ProsperAI challenge.',
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
  'home.morning': 'Good morning',
  'home.afternoon': 'Good afternoon',
  'home.evening': 'Good evening',
  'home.generate': 'Generate now',
  'home.generating': 'On air…',
  'home.emptyTitle': 'Your first episode is one click away',
  'home.emptyBody': 'The newsroom reads today’s news about your interests, checks the facts and records it for you. It takes about two minutes.',
  'home.listen': 'Listen',
  'home.previous': 'Previous episodes',
  'home.errorBusy': 'An episode is already being produced. Hang on, it’s almost ready.',
  'home.errorLimit': 'You reached today’s limit of episodes. Your next one arrives on schedule.',
  'home.min': 'min',
  'stage.queued': 'In the queue',
  'stage.fetching': 'Gathering the news',
  'stage.editing': 'Choosing the stories',
  'stage.researching': 'Reading the articles',
  'stage.writing': 'Writing the script',
  'stage.verifying': 'Checking the facts',
  'stage.recording': 'Recording',
  'stage.detail.fetching': '{candidates} stories from {outlets} outlets',
  'stage.detail.editing': 'The editor picked {n} stories',
  'stage.detail.researching': '{n} articles read in full',
  'stage.detail.verifyingOk': 'Every claim matches its sources',
  'stage.detail.verifyingFixed': 'Claims flagged: {found} · fixed: {fixed}',
  'stage.detail.recording': 'Part {done} of {total}',
  'stage.failed': 'Something went wrong while {stage}.',
  'stage.retry': 'Try again',
  'stage.ready': 'Your episode is ready',
}

export type Key = keyof typeof en

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
  'landing.demo.date': 'Resumen del martes',
  'landing.demo.title': 'Chips, chatbots y un gol en el descuento',
  'landing.demo.ch1': 'Buenos días, Ana',
  'landing.demo.ch2': 'Las reglas europeas de IA empiezan a notarse',
  'landing.demo.ch3': 'El chip que todos esperan',
  'landing.demo.ch4': 'El partido de anoche, en dos minutos',
  'landing.demo.hosts': 'con Sara y Martín',
  'landing.footer': 'Hecho para el reto de ProsperAI.',
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
  'home.morning': 'Buenos días',
  'home.afternoon': 'Buenas tardes',
  'home.evening': 'Buenas noches',
  'home.generate': 'Generar ahora',
  'home.generating': 'En antena…',
  'home.emptyTitle': 'Tu primer episodio está a un clic',
  'home.emptyBody': 'La redacción lee las noticias de hoy sobre tus temas, comprueba los hechos y te lo graba. Tarda unos dos minutos.',
  'home.listen': 'Escuchar',
  'home.previous': 'Episodios anteriores',
  'home.errorBusy': 'Ya hay un episodio en producción. Espera un poco, está casi listo.',
  'home.errorLimit': 'Has llegado al límite de episodios de hoy. El siguiente llegará a su hora.',
  'home.min': 'min',
  'stage.queued': 'En cola',
  'stage.fetching': 'Reuniendo noticias',
  'stage.editing': 'Eligiendo las historias',
  'stage.researching': 'Leyendo los artículos',
  'stage.writing': 'Escribiendo el guion',
  'stage.verifying': 'Comprobando los hechos',
  'stage.recording': 'Grabando',
  'stage.detail.fetching': '{candidates} noticias de {outlets} medios',
  'stage.detail.editing': 'El editor eligió {n} historias',
  'stage.detail.researching': '{n} artículos leídos enteros',
  'stage.detail.verifyingOk': 'Todas las afirmaciones cuadran con sus fuentes',
  'stage.detail.verifyingFixed': 'Afirmaciones revisadas: {found} · corregidas: {fixed}',
  'stage.detail.recording': 'Parte {done} de {total}',
  'stage.failed': 'Algo ha fallado en la etapa «{stage}».',
  'stage.retry': 'Reintentar',
  'stage.ready': 'Tu episodio está listo',
}

export const messages = { en, es }
export type Lang = keyof typeof messages
const STORAGE_KEY = 'ui-lang'

/** "Part {done} of {total}" + {done: 2, total: 5} → "Part 2 of 5". */
export function format(template: string, vars: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (_, name: string) => String(vars[name] ?? `{${name}}`))
}

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
