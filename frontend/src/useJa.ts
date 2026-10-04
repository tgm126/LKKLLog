import { useQuery, useQueryClient } from '@tanstack/react-query'

import { type Ja, nactiJa } from './api/ucet'

export const JA_KLIC = ['ja']

export function useJa() {
  return useQuery({ queryKey: JA_KLIC, queryFn: nactiJa, staleTime: 60_000 })
}

/** Po přihlášení/odhlášení uloží novou odpověď serveru a zahodí data předchozího uživatele. */
export function useNastavJa() {
  const klient = useQueryClient()
  return (ja: Ja) => {
    const ostatni = (dotaz: { queryKey: readonly unknown[] }) => dotaz.queryKey[0] !== JA_KLIC[0]
    klient.setQueryData(JA_KLIC, ja)
    klient.removeQueries({ predicate: ostatni, type: 'inactive' })
    void klient.invalidateQueries({ predicate: ostatni })
  }
}
