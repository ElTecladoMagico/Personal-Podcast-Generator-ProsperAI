import { UserButton } from '@clerk/react'
import { ChartColumn, House, Languages, Moon, Settings, Sun } from 'lucide-react'
import { useTheme } from 'next-themes'
import { NavLink, Outlet } from 'react-router'
import { Logo } from '@/components/Logo'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useMe } from '@/lib/api'
import { useT, type Lang } from '@/lib/i18n'
import { cn } from '@/lib/utils'

export function AppShell() {
  const { t } = useT()
  const { data: me } = useMe()
  const links = [
    { to: '/', label: t('nav.home'), icon: House },
    { to: '/settings', label: t('nav.settings'), icon: Settings },
    ...(me?.is_admin ? [{ to: '/admin', label: t('nav.admin'), icon: ChartColumn }] : []),
  ]

  return (
    <div className="min-h-svh">
      <header className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-5xl items-center gap-2 px-4">
          <NavLink to="/" className="mr-auto">
            <Logo />
          </NavLink>
          <nav className="flex items-center gap-1">
            {links.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                end
                aria-label={label}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-2 rounded-md px-2.5 py-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground',
                    isActive && 'bg-accent text-foreground',
                  )
                }
              >
                <Icon className="size-4" />
                <span className="hidden sm:inline">{label}</span>
              </NavLink>
            ))}
          </nav>
          <LanguageMenu />
          <ThemeToggle />
          <UserButton />
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-8">
        <Outlet />
      </main>
    </div>
  )
}

export function LanguageMenu() {
  const { lang, setLang, t } = useT()
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" aria-label={t('nav.language')}>
          <Languages />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuRadioGroup value={lang} onValueChange={(v) => setLang(v as Lang)}>
          <DropdownMenuRadioItem value="en">English</DropdownMenuRadioItem>
          <DropdownMenuRadioItem value="es">Español</DropdownMenuRadioItem>
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme()
  const { t } = useT()
  const dark = resolvedTheme === 'dark'
  return (
    <Button variant="ghost" size="icon" aria-label={t('nav.theme')} onClick={() => setTheme(dark ? 'light' : 'dark')}>
      {dark ? <Sun /> : <Moon />}
    </Button>
  )
}
