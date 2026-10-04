import { useInterval } from '@mantine/hooks'
import { useQuery } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'

import { nactiCiselniky, nactiPrehled } from './api/lety'

export const PREHLED_KLIC = ['prehled']

export function useCiselniky() {
  return useQuery({ queryKey: ['ciselniky'], queryFn: nactiCiselniky, staleTime: 5 * 60_000 })
}

/** Přehled dne se obnovuje každých 10 s a hned po návratu do aplikace (odemčení telefonu). */
export function usePrehled() {
  return useQuery({
    queryKey: PREHLED_KLIC,
    queryFn: nactiPrehled,
    refetchInterval: 10_000,
    refetchOnWindowFocus: true,
  })
}

/** Aktuální čas podle hodin serveru (telefon může mít hodiny posunuté). */
export function useServerovyCas(serverTed: string | undefined) {
  const posun = useRef(0)
  useEffect(() => {
    if (serverTed) posun.current = new Date(serverTed).getTime() - Date.now()
  }, [serverTed])
  const [ted, setTed] = useState(() => new Date())
  useInterval(() => setTed(new Date(Date.now() + posun.current)), 1000, { autoInvoke: true })
  return ted
}

/** Po změně letu se obnoví přehled dne i výpis. */
export const jeLetovyDotaz = (dotaz: { queryKey: readonly unknown[] }) =>
  dotaz.queryKey[0] === PREHLED_KLIC[0] || dotaz.queryKey[0] === 'vypis'
