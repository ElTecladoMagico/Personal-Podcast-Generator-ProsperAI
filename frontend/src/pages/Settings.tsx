import { useState } from 'react'
import { toast } from 'sonner'
import { FeedSection } from '@/components/FeedSection'
import { InterestsStep } from '@/components/onboarding/InterestsStep'
import { AvoidStep, HostsStep, ScheduleStep, SoundStep } from '@/components/onboarding/steps'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'
import { useMe } from '@/lib/api'
import { useT } from '@/lib/i18n'
import { type Preferences, useSavePreferences, useVoices, type Voice } from '@/lib/preferences'

/** The onboarding steps as one form: same components, one save button. */
export default function Settings() {
  const { data: me } = useMe()
  const { data: voices } = useVoices()
  if (!me || !voices) return <Skeleton className="h-96 w-full" />
  if (!me.preferences) return null
  return <SettingsForm initial={me.preferences} voices={voices} feedUrl={me.feed_url} />
}

function SettingsForm({ initial, voices, feedUrl }: { initial: Preferences; voices: Voice[]; feedUrl: string }) {
  const { t } = useT()
  const save = useSavePreferences()
  const [prefs, setPrefs] = useState(initial)
  const sections = [
    { title: 'onb.interests.title', body: <InterestsStep prefs={prefs} onChange={setPrefs} onImported={() => {}} /> },
    { title: 'onb.avoid.title', body: <AvoidStep prefs={prefs} onChange={setPrefs} voices={voices} /> },
    { title: 'onb.sound.title', body: <SoundStep prefs={prefs} onChange={setPrefs} voices={voices} /> },
    { title: 'onb.hosts.title', body: <HostsStep prefs={prefs} onChange={setPrefs} voices={voices} /> },
    { title: 'onb.schedule.title', body: <ScheduleStep prefs={prefs} onChange={setPrefs} voices={voices} /> },
  ] as const

  return (
    <div className="mx-auto max-w-2xl space-y-10 pb-24">
      <h1 className="text-4xl sm:text-5xl">{t('page.settings')}</h1>
      {sections.map((s, i) => (
        <section key={s.title} className="space-y-5">
          {i > 0 && <Separator />}
          <h2 className="text-3xl">{t(s.title)}</h2>
          {s.body}
        </section>
      ))}
      <section className="space-y-5">
        <Separator />
        <h2 className="text-3xl">{t('feed.title')}</h2>
        <FeedSection feedUrl={feedUrl} />
      </section>
      <footer className="sticky bottom-0 -mx-4 flex justify-end border-t bg-background/90 px-4 py-4 backdrop-blur">
        <Button size="lg" disabled={save.isPending || prefs.interests.length === 0}
          onClick={() => save.mutate({ preferences: prefs, method: 'manual' }, {
            onSuccess: () => toast.success(t('settings.saved')),
            onError: (err) => toast.error(err.message),
          })}>
          {t('settings.save')}
        </Button>
      </footer>
    </div>
  )
}
