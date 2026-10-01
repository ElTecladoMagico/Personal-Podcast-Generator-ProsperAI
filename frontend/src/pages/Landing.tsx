import { SignInButton } from '@clerk/react'
import { Logo } from '@/components/Logo'
import { Button } from '@/components/ui/button'
import { useT } from '@/lib/i18n'

// Full landing comes in the next commit.
export default function Landing() {
  const { t } = useT()
  return (
    <main className="grid min-h-svh place-content-center gap-6 p-4">
      <Logo />
      <SignInButton mode="modal">
        <Button>{t('auth.signIn')}</Button>
      </SignInButton>
    </main>
  )
}
