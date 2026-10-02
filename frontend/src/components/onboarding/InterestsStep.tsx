import { Copy, Sparkles, X } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { format, useT } from '@/lib/i18n'
import { addInterest, IMPORT_PROMPT, mergeImported, type Preferences, SUGGESTIONS, useImportPreferences } from '@/lib/preferences'
import { cn } from '@/lib/utils'

const ASSISTANTS = [
  { name: 'ChatGPT', url: 'https://chatgpt.com/' },
  { name: 'Claude', url: 'https://claude.ai/new' },
  { name: 'Gemini', url: 'https://gemini.google.com/app' },
]

export function InterestsStep({ prefs, onChange, onImported }: {
  prefs: Preferences
  onChange: (prefs: Preferences) => void
  onImported: () => void
}) {
  const { t, lang } = useT()
  const importer = useImportPreferences()
  const [pasted, setPasted] = useState('')
  const [topic, setTopic] = useState('')
  const interests = prefs.interests

  const copyPrompt = async () => {
    await navigator.clipboard.writeText(IMPORT_PROMPT[lang])
    toast.success(t('onb.import.copied'))
  }
  const runImport = () =>
    importer.mutate(pasted, {
      onSuccess: (imported) => {
        onChange(mergeImported(prefs, imported))
        onImported()
        setPasted('')
        toast.success(format(t('onb.import.done'), { n: imported.interests.length }))
      },
      onError: (err) => toast.error(err.message),
    })
  const setInterests = (next: Preferences['interests']) => onChange({ ...prefs, interests: next })
  const toggle = (name: string) =>
    interests.some((i) => i.topic === name)
      ? setInterests(interests.filter((i) => i.topic !== name))
      : setInterests(addInterest(interests, name))

  return (
    <div className="space-y-8">
      <section className="space-y-4 rounded-2xl border border-primary/40 bg-primary/5 p-5">
        <div className="flex items-start gap-3">
          <Sparkles className="mt-1 size-5 shrink-0 text-primary" />
          <div className="space-y-1">
            <h2 className="text-2xl">{t('onb.import.cta')}</h2>
            <p className="text-sm text-muted-foreground">{t('onb.import.desc')}</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button onClick={copyPrompt}>
            <Copy /> {t('onb.import.copy')}
          </Button>
          {ASSISTANTS.map((a) => (
            <Button key={a.name} variant="outline" asChild>
              <a href={a.url} target="_blank" rel="noreferrer">{a.name} ↗</a>
            </Button>
          ))}
        </div>
        <Textarea value={pasted} onChange={(e) => setPasted(e.target.value)} placeholder={t('onb.import.paste')}
          aria-label={t('onb.import.paste')} className="max-h-40 min-h-24 overflow-y-auto font-mono text-xs" />
        <Button variant="secondary" disabled={!pasted.trim() || importer.isPending} onClick={runImport}>
          {t('onb.import.button')}
        </Button>
      </section>

      {interests.length > 0 && (
        <ul className="flex flex-wrap gap-2" aria-live="polite">
          {interests.map((interest, i) => (
            <li key={interest.topic}
              className="flex items-center gap-2 rounded-full border bg-card py-1 pr-1.5 pl-3.5 motion-safe:animate-in motion-safe:zoom-in-90 motion-safe:fade-in motion-safe:fill-mode-both"
              style={{ animationDelay: `${Math.min(i, 10) * 50}ms` }}>
              <span className="text-sm">{interest.topic}</span>
              <span className="flex" role="group" aria-label={interest.topic}>
                {[1, 2, 3, 4, 5].map((w) => (
                  <button key={w} type="button"
                    aria-label={format(t('onb.weight'), { topic: interest.topic, n: w })}
                    aria-pressed={(interest.weight ?? 3) === w}
                    onClick={() => setInterests(interests.map((x) => (x === interest ? { ...x, weight: w } : x)))}
                    className="p-0.5">
                    <span className={cn('block size-1.5 rounded-full', w <= (interest.weight ?? 3) ? 'bg-primary' : 'bg-muted-foreground/30')} />
                  </button>
                ))}
              </span>
              <button type="button" aria-label={format(t('onb.remove'), { topic: interest.topic })}
                onClick={() => setInterests(interests.filter((x) => x !== interest))}
                className="rounded-full p-1 text-muted-foreground hover:bg-accent hover:text-foreground">
                <X className="size-3.5" />
              </button>
            </li>
          ))}
        </ul>
      )}

      <Input value={topic} placeholder={t('onb.add')} aria-label={t('onb.add')}
        onChange={(e) => setTopic(e.target.value)}
        onKeyDown={(e) => {
          if (e.key !== 'Enter') return
          e.preventDefault()
          setInterests(addInterest(interests, topic))
          setTopic('')
        }} />

      <section className="space-y-3">
        <p className="text-sm text-muted-foreground">{t('onb.suggestions')}</p>
        {Object.entries(SUGGESTIONS[lang]).map(([category, topics]) => (
          <div key={category} className="flex flex-wrap items-center gap-2">
            <span className="w-24 text-xs tracking-widest text-muted-foreground uppercase">{category}</span>
            {topics.map((name) => {
              const on = interests.some((i) => i.topic === name)
              return (
                <button key={name} type="button" aria-pressed={on} onClick={() => toggle(name)}
                  className={cn('rounded-full border px-3 py-1 text-sm transition-colors',
                    on ? 'border-primary bg-primary/10 text-primary' : 'text-muted-foreground hover:text-foreground')}>
                  {name}
                </button>
              )
            })}
          </div>
        ))}
      </section>
    </div>
  )
}
