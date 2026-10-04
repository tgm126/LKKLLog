import { Anchor, Select } from '@mantine/core'
import { useState } from 'react'

import type { PolozkaOsoby } from '../posadka'

/** Výběr osoby: nabízí jen doporučené (podle oprávnění), ostatní až na požádání.
 *
 * Když doporučený nikdo není (číselník oprávnění ještě není kompletní), ukáže všechny.
 */
export function VyberOsoby({
  label,
  nabidka,
  value,
  onChange,
  searchable,
}: {
  label: string
  nabidka: { doporuceni: PolozkaOsoby[]; ostatni: PolozkaOsoby[] }
  value: string | null
  onChange: (v: string | null) => void
  searchable: boolean
}) {
  const [vse, setVse] = useState(false)
  const { doporuceni, ostatni } = nabidka
  const nikdo = doporuceni.length === 0
  // Už vybraná osoba mimo doporučené (např. u opravy letu) musí být v nabídce vidět.
  const vybrany = ostatni.find((o) => o.value === value)
  const data =
    nikdo || vse
      ? [
          ...(doporuceni.length ? [{ group: 'Doporučení', items: doporuceni }] : []),
          ...(ostatni.length ? [{ group: nikdo ? 'Všichni' : 'Ostatní', items: ostatni }] : []),
        ]
      : [...doporuceni, ...(vybrany ? [vybrany] : [])]
  return (
    <div>
      <Select
        label={label}
        size="md"
        searchable={searchable}
        data={data}
        value={value}
        onChange={onChange}
        nothingFoundMessage="Nikdo takový"
        description={nikdo && ostatni.length ? 'Nikdo nemá v číselníku oprávnění – nabízím všechny.' : undefined}
      />
      {!nikdo && ostatni.length > 0 && (
        <Anchor component="button" type="button" fz="sm" mt={4} onClick={() => setVse(!vse)}>
          {vse ? 'Jen doporučení' : `Ukázat i ostatní (${ostatni.length})`}
        </Anchor>
      )}
    </div>
  )
}
