import '@mantine/core/styles.css'
import '@mantine/notifications/styles.css'

import { createTheme, MantineProvider } from '@mantine/core'
import { Notifications } from '@mantine/notifications'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import App from './App.tsx'

const theme = createTheme({
  primaryColor: 'blue',
  // Větší výchozí velikosti – ovládá se prsty na mobilu, často venku na slunci.
  defaultRadius: 'md',
})

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Po odemčení telefonu nebo návratu do okna se data hned obnoví.
      refetchOnWindowFocus: true,
      retry: 1,
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <MantineProvider theme={theme} defaultColorScheme="auto">
      <Notifications position="top-center" />
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </MantineProvider>
  </StrictMode>,
)
