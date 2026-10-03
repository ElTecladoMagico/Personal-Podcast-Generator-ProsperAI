import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from 'next-themes'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { LocalizedClerk } from '@/components/LocalizedClerk'
import { Toaster } from '@/components/ui/sonner'
import { TooltipProvider } from '@/components/ui/tooltip'
import { I18nProvider } from '@/lib/i18n'
import App from './App.tsx'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
})

const clerkKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY
if (!clerkKey) throw new Error('Missing VITE_CLERK_PUBLISHABLE_KEY (see frontend/.env.example)')

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <I18nProvider>
      <LocalizedClerk publishableKey={clerkKey}>
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false}>
          <QueryClientProvider client={queryClient}>
            <TooltipProvider>
              <App />
              <Toaster />
            </TooltipProvider>
          </QueryClientProvider>
        </ThemeProvider>
      </LocalizedClerk>
    </I18nProvider>
  </StrictMode>,
)
