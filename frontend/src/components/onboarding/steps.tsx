import { Check, Mic, MicVocal, Play, Square, Users } from 'lucide-react'
import { useRef, useState } from 'react'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { format, useT } from '@/lib/i18n'
import { defaultHosts, type Format, hostsForFormat, LANGUAGES, type Preferences, type Voice } from '@/lib/preferences'
import { cn } from '@/lib/utils'
import { Choice, TagInput } from './fields'

type StepProps = { prefs: Preferences; onChange: (prefs: Preferences) => void; voices: Voice[] }

export function AvoidStep({ prefs, onChange }: StepProps) {
  const { t } = useT()
  return (
    <div className="space-y-8">
      <TagInput label={t('onb.avoid.label')} placeholder={t('onb.avoid.add')} values={prefs.avoid ?? []}
        onChange={(avoid) => onChange({ ...prefs, avoid })} />
      <TagInput label={t('onb.trusted.title')} placeholder={t('onb.trusted.add')} values={prefs.sources_i_trust ?? []}
        onChange={(sources_i_trust) => onChange({ ...prefs, sources_i_trust })} />
    </div>
  )
}

const FORMATS: { value: Format; icon: typeof Mic }[] = [
  { value: 'solo', icon: Mic },
  { value: 'duo', icon: Users },
  { value: 'debate', icon: MicVocal },
]

export function SoundStep({ prefs, onChange, voices }: StepProps) {
  const { t } = useT()
  const setFormat = (f: Format) =>
    onChange({ ...prefs, format: f, hosts: hostsForFormat(f, prefs.hosts, voices, prefs.language ?? 'en') })
  // Untouched default hosts follow the language (native voices); hand-picked ones stay.
  const setLanguage = (language: Preferences['language']) => {
    const same = (a: Preferences['hosts'], b: Preferences['hosts']) => a.map((h) => h.voice_id).join() === b.map((h) => h.voice_id).join()
    const wasDefault = same(prefs.hosts, hostsForFormat(prefs.format ?? 'duo', defaultHosts(voices, prefs.language ?? 'en'), voices, prefs.language ?? 'en'))
    const hosts = wasDefault ? hostsForFormat(prefs.format ?? 'duo', defaultHosts(voices, language), voices, language) : prefs.hosts
    onChange({ ...prefs, language, hosts })
  }
  return (
    <div className="space-y-8">
      <Choice label={t('onb.language')} value={prefs.language ?? 'en'} onChange={setLanguage}
        options={LANGUAGES.map((l) => ({ value: l.code, label: l.label }))} />
      <div className="space-y-2">
        <Label>{t('onb.format')}</Label>
        <div className="grid gap-3 sm:grid-cols-3" role="radiogroup" aria-label={t('onb.format')}>
          {FORMATS.map(({ value, icon: Icon }) => {
            const on = prefs.format === value
            return (
              <button key={value} type="button" role="radio" aria-checked={on} onClick={() => setFormat(value)}
                className={cn('space-y-2 rounded-xl border p-4 text-left transition-colors',
                  on ? 'border-primary bg-primary/5' : 'hover:border-foreground/30')}>
                <Icon className={cn('size-5', on ? 'text-primary' : 'text-muted-foreground')} />
                <p className="font-medium">{t(`format.${value}`)}</p>
                <p className="text-sm text-muted-foreground">{t(`format.${value}.desc`)}</p>
              </button>
            )
          })}
        </div>
      </div>
      <Choice label={t('onb.tone')} value={prefs.tone ?? 'casual'} onChange={(tone) => onChange({ ...prefs, tone })}
        options={(['casual', 'serious', 'nerdy'] as const).map((v) => ({ value: v, label: t(`tone.${v}`) }))} />
      <Choice label={t('onb.depth')} value={prefs.depth ?? 'analysis'} onChange={(depth) => onChange({ ...prefs, depth })}
        options={(['headlines', 'analysis'] as const).map((v) => ({ value: v, label: t(`depth.${v}`) }))} />
      <Choice label={t('onb.duration')} value={prefs.duration_min ?? 10} onChange={(duration_min) => onChange({ ...prefs, duration_min })}
        options={([5, 10] as const).map((v) => ({ value: v, label: `${v} min` }))} />
    </div>
  )
}

export function HostsStep({ prefs, onChange, voices }: StepProps) {
  const { t, lang } = useT()
  const wanted = prefs.format === 'solo' ? 1 : 2
  const audio = useRef<HTMLAudioElement | null>(null)
  const [playing, setPlaying] = useState<string>()
  const native = voices.filter((v) => v.language === prefs.language)
  const others = voices.filter((v) => v.language !== prefs.language)

  const play = (v: Voice) => {
    audio.current?.pause()
    if (playing === v.id) return setPlaying(undefined)
    audio.current = new Audio(v.preview)
    audio.current.onended = () => setPlaying(undefined)
    void audio.current.play()
    setPlaying(v.id)
  }
  const select = (v: Voice) => {
    const chosen = prefs.hosts.some((h) => h.voice_id === v.id)
    let hosts = chosen ? prefs.hosts.filter((h) => h.voice_id !== v.id) : [...prefs.hosts, { name: v.name, voice_id: v.id }]
    if (hosts.length > wanted) hosts = hosts.slice(-wanted)  // keep the newest picks
    if (hosts.length) onChange({ ...prefs, hosts })
  }

  const card = (v: Voice) => {
    const host = prefs.hosts.find((h) => h.voice_id === v.id)
    return (
      <li key={v.id} className={cn('flex items-center gap-3 rounded-xl border p-3 transition-colors', host && 'border-primary bg-primary/5')}>
        <button type="button" onClick={() => play(v)} aria-label={format(t('onb.play'), { name: v.name })}
          className="grid size-10 shrink-0 place-items-center rounded-full bg-accent text-foreground hover:bg-primary hover:text-primary-foreground">
          {playing === v.id ? <Square className="size-4" /> : <Play className="size-4" />}
        </button>
        <button type="button" onClick={() => select(v)} aria-pressed={Boolean(host)} className="min-w-0 flex-1 text-left">
          <p className="font-medium">{v.name}</p>
          <p className="truncate text-sm text-muted-foreground">{v.descriptor[lang]}</p>
        </button>
        {host && <Check className="size-5 text-primary" aria-label={t('onb.selected')} />}
      </li>
    )
  }

  return (
    <div className="space-y-6">
      <p className="text-muted-foreground">{format(t('onb.hosts.pick'), { n: wanted })}</p>
      {native.length > 0 && (
        <section className="space-y-2">
          <h3 className="text-xs tracking-widest text-muted-foreground uppercase">{t('onb.hosts.native')}</h3>
          <ul className="grid gap-2 sm:grid-cols-2">{native.map(card)}</ul>
        </section>
      )}
      <section className="space-y-2">
        <h3 className="text-xs tracking-widest text-muted-foreground uppercase">{t('onb.hosts.others')}</h3>
        <ul className="grid gap-2 sm:grid-cols-2">{others.map(card)}</ul>
      </section>
      <section className="grid gap-3 sm:grid-cols-2">
        {prefs.hosts.map((h, i) => (
          <div key={h.voice_id} className="space-y-1">
            <Label htmlFor={`host-${i}`}>{t('onb.hosts.name')} · {voices.find((v) => v.id === h.voice_id)?.name}</Label>
            <Input id={`host-${i}`} value={h.name} maxLength={30}
              onChange={(e) => onChange({ ...prefs, hosts: prefs.hosts.map((x, j) => (j === i ? { ...x, name: e.target.value } : x)) })} />
          </div>
        ))}
      </section>
    </div>
  )
}

export function ScheduleStep({ prefs, onChange }: StepProps) {
  const { t, lang } = useT()
  const schedule = prefs.schedule ?? { frequency: 'daily', time: '07:00', weekday: null, timezone: 'Europe/Madrid' }
  const set = (patch: Partial<typeof schedule>) => onChange({ ...prefs, schedule: { ...schedule, ...patch } })
  const dayName = (i: number) => new Date(2026, 0, 5 + i).toLocaleDateString(lang, { weekday: 'long' })  // 2026-01-05 is a Monday
  return (
    <div className="space-y-8">
      <Choice label={t('onb.frequency')} value={schedule.frequency ?? 'daily'}
        onChange={(frequency) => set({ frequency, weekday: frequency === 'weekly' ? (schedule.weekday ?? 0) : null })}
        options={(['daily', 'weekdays', 'weekly', 'off'] as const).map((v) => ({ value: v, label: t(`freq.${v}`) }))} />
      {schedule.frequency === 'weekly' && (
        <Choice label={t('onb.weekday')} value={schedule.weekday ?? 0} onChange={(weekday) => set({ weekday })}
          options={[0, 1, 2, 3, 4, 5, 6].map((i) => ({ value: i, label: dayName(i) }))} />
      )}
      {schedule.frequency !== 'off' && (
        <div className="flex flex-wrap gap-6">
          <div className="space-y-2">
            <Label htmlFor="time">{t('onb.time')}</Label>
            <Input id="time" type="time" value={schedule.time} onChange={(e) => set({ time: e.target.value })} className="w-36" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="tz">{t('onb.timezone')}</Label>
            <select id="tz" value={schedule.timezone} onChange={(e) => set({ timezone: e.target.value })}
              className="h-10 w-64 rounded-md border bg-background px-3">
              {Intl.supportedValuesOf('timeZone').map((z) => <option key={z} value={z}>{z.replaceAll('_', ' ')}</option>)}
            </select>
          </div>
        </div>
      )}
    </div>
  )
}
