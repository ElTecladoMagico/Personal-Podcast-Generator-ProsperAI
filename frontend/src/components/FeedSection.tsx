import { Copy, Podcast, RefreshCw } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import {
  Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { podcastApps, useRotateFeedToken } from '@/lib/feed'
import { useT } from '@/lib/i18n'

/** The private RSS link, ready to paste or to open straight in a podcast app. */
export function FeedSection({ feedUrl }: { feedUrl: string }) {
  const { t } = useT()
  const rotate = useRotateFeedToken()
  const copy = () => navigator.clipboard.writeText(feedUrl).then(() => toast.success(t('feed.copied')))

  return (
    <div className="space-y-4">
      <p className="text-muted-foreground">{t('feed.body')}</p>
      <div className="flex gap-2">
        <Input readOnly value={feedUrl} aria-label={t('feed.title')} onFocus={(e) => e.target.select()} className="font-mono text-xs" />
        <Button variant="secondary" onClick={copy}><Copy /> {t('feed.copy')}</Button>
      </div>
      <div className="flex flex-wrap gap-2">
        {podcastApps(feedUrl).map((app) => (
          <Button key={app.name} variant="outline" asChild>
            <a href={app.href}><Podcast /> {app.name}</a>
          </Button>
        ))}
      </div>
      <p className="text-xs text-muted-foreground">{t('feed.appsNote')}</p>
      <Dialog>
        <DialogTrigger asChild>
          <Button variant="ghost" size="sm" className="-ml-2 text-muted-foreground"><RefreshCw /> {t('feed.rotate')}</Button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('feed.rotateTitle')}</DialogTitle>
            <DialogDescription>{t('feed.rotateBody')}</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <DialogClose asChild><Button variant="outline">{t('feed.cancel')}</Button></DialogClose>
            <DialogClose asChild>
              <Button variant="destructive" disabled={rotate.isPending}
                onClick={() => rotate.mutate(undefined, { onSuccess: () => toast.success(t('feed.rotated')), onError: (e) => toast.error(e.message) })}>
                {t('feed.rotate')}
              </Button>
            </DialogClose>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
