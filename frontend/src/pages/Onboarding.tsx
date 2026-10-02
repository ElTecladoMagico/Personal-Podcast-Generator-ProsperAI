import { ArrowLeft } from 'lucide-react'
import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router'
import { toast } from 'sonner'
import { InterestsStep } from '@/components/onboarding/InterestsStep'
import { AvoidStep, HostsStep, ScheduleStep, SoundStep } from '@/components/onboarding/steps'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useMe } from '@/lib/api'
import { useGenerate } from '@/lib/episodes'
import { format, useT } from '@/lib/i18n'
import { newPreferences, type Preferences, useSavePreferences, useVoices, type Voice } from '@/lib/preferences'

const STEPS = [
  { title: 'onb.interests.title', subtitle: 'onb.interests.subtitle', Body: InterestsStep },
  { title: 'onb.avoid.title', subtitle: 'onb.avoid.subtitle', Body: AvoidStep },
  { title: 'onb.sound.title', subtitle: null, Body: SoundStep },
  { title: 'onb.hosts.title', subtitle: null, Body: HostsStep },
  { title: 'onb.schedule.title', subtitle: null, Body: ScheduleStep },
] as const

export default function Onboarding() {
  const { data: me } = useMe()
  const { data: voices } = useVoices()
  if (me?.onboarded) return <Navigate to="/" replace />
  if (!me || !voices) return <Skeleton className="h-96 w-full" />
  return <Wizard voices={voices} />
}

function Wizard({ voices }: { voices: Voice[] }) {
  const { t, lang } = useT()
  const navigate = useNavigate()
  const save = useSavePreferences()
  const generate = useGenerate()
  const [step, setStep] = useState(0)
  const [imported, setImported] = useState(false)
  const [prefs, setPrefs] = useState<Preferences>(() =>
    newPreferences(lang, Intl.DateTimeFormat().resolvedOptions().timeZone, voices),
  )
  const { title, subtitle, Body } = STEPS[step]
  const last = step === STEPS.length - 1
  const canContinue = step !== 0 || prefs.interests.length > 0
  const busy = save.isPending || generate.isPending

  const finish = () =>
    save.mutate(
      { preferences: prefs, method: imported ? 'import' : 'manual' },
      {
        onSuccess: () =>
          generate.mutate(undefined, {
            onSettled: () => {
              toast.success(t('onb.firstEpisode'))
              navigate('/', { replace: true })
            },
          }),
        onError: (err) => toast.error(err.message),
      },
    )

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <div className="space-y-3">
        <p className="text-xs tracking-widest text-muted-foreground uppercase">
          {format(t('onb.step'), { n: step + 1, total: STEPS.length })}
        </p>
        <div className="flex gap-1.5" aria-hidden>
          {STEPS.map((_, i) => (
            <span key={i} className={`h-1 flex-1 rounded-full transition-colors duration-300 ${i <= step ? 'bg-primary' : 'bg-muted'}`} />
          ))}
        </div>
      </div>

      <section key={step} className="space-y-6 motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-right-4 motion-safe:duration-300">
        <header className="space-y-2">
          <h1 className="text-4xl sm:text-5xl">{t(title)}</h1>
          {subtitle && <p className="text-muted-foreground">{t(subtitle)}</p>}
        </header>
        <Body prefs={prefs} onChange={setPrefs} voices={voices} onImported={() => setImported(true)} />
        {step === 0 && !canContinue && <p className="text-sm text-muted-foreground">{t('onb.interests.empty')}</p>}
      </section>

      <footer className="sticky bottom-0 -mx-4 flex items-center gap-3 border-t bg-background/90 px-4 py-4 backdrop-blur">
        {step > 0 && (
          <Button variant="ghost" onClick={() => setStep(step - 1)} disabled={busy}>
            <ArrowLeft /> {t('onb.back')}
          </Button>
        )}
        <div className="flex-1" />
        {step === 1 && (
          <Button variant="ghost" onClick={() => setStep(2)}>
            {t('onb.skip')}
          </Button>
        )}
        <Button size="lg" disabled={!canContinue || busy} onClick={() => (last ? finish() : setStep(step + 1))}>
          {busy ? t('onb.finishing') : last ? t('onb.finish') : t('onb.next')}
        </Button>
      </footer>
    </div>
  )
}
