import { esES } from '@clerk/localizations'
import { ClerkProvider } from '@clerk/react'
import { shadcn } from '@clerk/ui/themes'
import type { ReactNode } from 'react'
import { useT } from '@/lib/i18n'

/** Clerk's sign-in follows the app's language (English is Clerk's default). */
export function LocalizedClerk({ publishableKey, children }: { publishableKey: string; children: ReactNode }) {
  const { lang } = useT()
  return (
    <ClerkProvider publishableKey={publishableKey} afterSignOutUrl="/" appearance={{ theme: shadcn }}
      localization={lang === 'es' ? esES : undefined}>
      {children}
    </ClerkProvider>
  )
}
