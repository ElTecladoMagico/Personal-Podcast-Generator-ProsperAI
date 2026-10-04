import { SendHorizontal } from 'lucide-react'
import { type FormEvent, useEffect, useRef, useState } from 'react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { ApiError } from '@/lib/api'
import { activeTurn, type Answer, useAsk } from '@/lib/ask'
import { useT } from '@/lib/i18n'
import { cn } from '@/lib/utils'
import { hostColor } from './hostColor'

const SUGGESTIONS = ['ask.s1', 'ask.s2', 'ask.s3', 'ask.s4'] as const

/** The hosts answer a question about the story at `at` seconds, out loud (ADR 0014). The page
 *  pauses the episode before opening this (`at` set) and resumes it in `onClose`. */
export function AskHosts({ episodeId, hosts, at, onClose }: {
  episodeId: string
  hosts: string[]
  at: number | null // where the episode was paused; null = closed
  onClose: () => void
}) {
  const { t } = useT()
  const ask = useAsk(episodeId)
  const answerAudio = useRef<HTMLAudioElement>(null)
  const [question, setQuestion] = useState('')
  const [history, setHistory] = useState<{ question: string; answer: Answer }[]>([])
  const [clock, setClock] = useState({ time: 0, duration: 0, playing: false })

  // Closing (button, Esc, tapping outside or the answer ending) stops the answer.
  const close = () => {
    answerAudio.current?.pause()
    onClose()
  }
  const send = (text: string) => {
    const q = text.trim()
    if (q.length < 3 || ask.isPending) return
    ask.mutate({ question: q, position_s: at ?? 0 }, {
      onSuccess: (answer) => {
        setHistory((h) => [...h, { question: q, answer }])
        setQuestion('')
      },
      onError: (err) => toast.error(err instanceof ApiError && err.status === 429 ? t('ask.limit') : t('ask.error')),
    })
  }
  const latest = history.at(-1)

  // Play each new answer as soon as it arrives.
  useEffect(() => {
    const audio = answerAudio.current
    if (!audio || !latest) return
    audio.src = latest.answer.audio_url
    void audio.play()
  }, [latest])

  return (
    <>
      <audio ref={answerAudio} preload="auto" onEnded={close}
        onTimeUpdate={(e) => setClock({ time: e.currentTarget.currentTime, duration: e.currentTarget.duration, playing: true })}
        onPause={() => setClock((c) => ({ ...c, playing: false }))} />
      <Sheet open={at !== null} onOpenChange={(o) => !o && close()}>
        <SheetContent side="bottom" className="mx-auto max-h-[85svh] w-full max-w-2xl gap-0 rounded-t-2xl">
          <SheetHeader>
            <SheetTitle className="font-heading text-2xl font-normal">{t('ask.button')}</SheetTitle>
            <SheetDescription>{t('ask.hint')}</SheetDescription>
          </SheetHeader>

          <div className="space-y-4 overflow-y-auto px-4 pb-4">
            {history.map(({ question: q, answer }, i) => {
              const live = i === history.length - 1 && clock.playing
              const current = live ? activeTurn(answer.turns, clock.time, clock.duration) : -1
              return (
                <div key={answer.qid} className="space-y-2">
                  <p className="ml-auto w-fit max-w-[85%] rounded-2xl rounded-br-sm bg-primary/15 px-3 py-2 text-sm">
                    <span className="sr-only">{t('ask.you')}: </span>{q}
                  </p>
                  {answer.turns.map((turn, ti) => (
                    <p key={ti} className={cn('max-w-[90%] rounded-2xl rounded-bl-sm px-3 py-2 text-sm transition-colors',
                      ti === current ? 'bg-accent text-foreground' : 'bg-muted/50 text-muted-foreground')}>
                      <span className="block text-xs font-medium" style={{ color: hostColor(turn.speaker) }}>
                        {hosts[turn.speaker]}
                      </span>
                      {turn.text}
                    </p>
                  ))}
                </div>
              )
            })}

            {ask.isPending && (
              <p className="flex items-center gap-2 text-sm text-muted-foreground" role="status">
                <span className="flex gap-1" aria-hidden>
                  {[0, 1, 2].map((d) => (
                    <span key={d} className="size-1.5 rounded-full bg-primary motion-safe:animate-bounce"
                      style={{ animationDelay: `${d * 150}ms` }} />
                  ))}
                </span>
                {hosts.join(' · ')} · {t('ask.thinking')}
              </p>
            )}

            {!history.length && !ask.isPending && (
              <div className="flex flex-wrap gap-2">
                {SUGGESTIONS.map((key) => (
                  <Button key={key} variant="outline" size="sm" className="rounded-full" onClick={() => send(t(key))}>
                    {t(key)}
                  </Button>
                ))}
              </div>
            )}

            <form className="flex gap-2" onSubmit={(e: FormEvent) => { e.preventDefault(); send(question) }}>
              <Input value={question} onChange={(e) => setQuestion(e.target.value)} maxLength={300}
                placeholder={t('ask.placeholder')} aria-label={t('ask.placeholder')} disabled={ask.isPending} autoFocus />
              <Button type="submit" disabled={ask.isPending || question.trim().length < 3}>
                <SendHorizontal /> <span className="max-sm:sr-only">{t('ask.send')}</span>
              </Button>
            </form>
            <Button variant="ghost" className="w-full" onClick={close}>{t('ask.back')}</Button>
          </div>
        </SheetContent>
      </Sheet>
    </>
  )
}
