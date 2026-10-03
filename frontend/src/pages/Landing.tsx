import { SignInButton, SignUpButton } from '@clerk/react'
import type { CSSProperties } from 'react'
import { BellRing, ShieldCheck, Sparkles } from 'lucide-react'
import { LanguageMenu, ThemeToggle } from '@/components/AppShell'
import { Logo } from '@/components/Logo'
import { Button } from '@/components/ui/button'
import { useT } from '@/lib/i18n'

export default function Landing() {
  const { t } = useT()
  const benefits = [
    { icon: Sparkles, title: t('landing.benefit1.title'), body: t('landing.benefit1.body') },
    { icon: BellRing, title: t('landing.benefit2.title'), body: t('landing.benefit2.body') },
    { icon: ShieldCheck, title: t('landing.benefit3.title'), body: t('landing.benefit3.body') },
  ]

  return (
    <div className="min-h-svh">
      <header className="mx-auto flex h-14 max-w-6xl items-center gap-2 px-4">
        <span className="mr-auto">
          <Logo />
        </span>
        <LanguageMenu />
        <ThemeToggle />
        <SignInButton mode="modal">
          <Button variant="ghost">{t('auth.signIn')}</Button>
        </SignInButton>
      </header>

      <main className="mx-auto max-w-6xl px-4">
        <section className="grid items-center gap-12 py-16 md:grid-cols-[1.1fr_1fr] md:py-24">
          <div className="space-y-8 motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-4 motion-safe:duration-500">
            <OnAirPill label={t('landing.onAir')} />
            <h1 className="text-6xl leading-[0.95] sm:text-7xl lg:text-8xl">
              {t('landing.title1')}
              <br />
              {t('landing.title2')}
              <br />
              <em className="text-primary">{t('landing.title3')}</em>
            </h1>
            <p className="max-w-md text-lg text-muted-foreground">{t('landing.subtitle')}</p>
            <div className="flex flex-wrap gap-3">
              <SignUpButton mode="modal">
                <Button size="lg">{t('auth.getStarted')}</Button>
              </SignUpButton>
              <SignInButton mode="modal">
                <Button size="lg" variant="outline">
                  {t('auth.signIn')}
                </Button>
              </SignInButton>
            </div>
          </div>
          <DemoEpisode />
        </section>

        <section className="grid gap-8 border-t py-16 sm:grid-cols-3">
          {benefits.map(({ icon: Icon, title, body }) => (
            <div key={title} className="space-y-3">
              <Icon className="size-5 text-signal" />
              <h2 className="text-2xl">{title}</h2>
              <p className="text-muted-foreground">{body}</p>
            </div>
          ))}
        </section>
      </main>

      <footer className="mx-auto max-w-6xl px-4 py-8 text-sm text-muted-foreground">{t('landing.footer')}</footer>
    </div>
  )
}

function OnAirPill({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-primary/40 px-3 py-1 text-xs font-medium tracking-widest text-primary uppercase">
      <span className="size-1.5 rounded-full bg-primary motion-safe:animate-pulse" />
      {label}
    </span>
  )
}

/** A static "now playing" card: shows what the product makes before anyone signs in. */
function DemoEpisode() {
  const { t } = useT()
  const chapters = [
    ['0:00', t('landing.demo.ch1')],
    ['0:42', t('landing.demo.ch2')],
    ['3:15', t('landing.demo.ch3')],
    ['6:30', t('landing.demo.ch4')],
  ]
  return (
    <div className="rounded-2xl border bg-card p-6 shadow-2xl shadow-primary/5 motion-safe:animate-in motion-safe:fade-in motion-safe:delay-150 motion-safe:duration-700">
      <p className="text-xs tracking-widest text-muted-foreground uppercase">{t('landing.demo.date')} · 10 min</p>
      <h2 className="mt-2 text-3xl">{t('landing.demo.title')}</h2>
      <p className="mt-1 text-sm text-muted-foreground">{t('landing.demo.hosts')}</p>
      <Waveform />
      <ol className="space-y-1">
        {chapters.map(([time, title], i) => (
          <li
            key={time}
            className={`flex gap-4 rounded-md px-3 py-2 text-sm ${i === 1 ? 'bg-accent text-foreground' : 'text-muted-foreground'}`}
          >
            <span className="w-10 tabular-nums">{time}</span>
            <span>{title}</span>
          </li>
        ))}
      </ol>
    </div>
  )
}

function Waveform() {
  const bars = Array.from({ length: 48 }, (_, i) => 0.3 + 0.7 * Math.abs(Math.sin(i * 1.7) * Math.cos(i * 0.4)))
  return (
    <div className="my-6 flex h-16 items-center gap-[3px]" aria-hidden>
      {bars.map((height, i) => (
        <span
          key={i}
          className={`wave-bar w-full rounded-full ${i < 14 ? 'bg-primary' : 'bg-muted-foreground/30'}`}
          style={
            {
              height: `${height * 100}%`,
              '--wave-duration': `${1.2 + (i % 5) * 0.25}s`,
              '--wave-delay': `${(i % 7) * -0.2}s`,
            } as CSSProperties
          }
        />
      ))}
    </div>
  )
}
