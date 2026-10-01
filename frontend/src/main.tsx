import { ClerkProvider } from '@clerk/react'
import { shadcn } from '@clerk/ui/themes'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from 'next-themes'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
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
    <ClerkProvider publishableKey={clerkKey} afterSignOutUrl="/" appearance={{ theme: shadcn }}>
      <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false}>
        <QueryClientProvider client={queryClient}>
          <I18nProvider>
            <TooltipProvider>
              <App />
              <Toaster />
            </TooltipProvider>
          </I18nProvider>
        </QueryClientProvider>
      </ThemeProvider>
    </ClerkProvider>
  </StrictMode>,
)
