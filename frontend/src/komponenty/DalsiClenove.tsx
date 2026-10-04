import { Button, MultiSelect, Stack } from '@mantine/core'

import type { OsobaVyber } from '../api/lety'
import { jmeno } from '../posadka'

/** Další členové aeroklubu na palubě (u normálního letu) a prohození rolí s PIC. */
export function DalsiClenove({
  osoby,
  pic,
  hodnota,
  onZmena,
  onProhodit,
  veVzduchu,
  hledani,
  maxPocet,
}: {
  osoby: OsobaVyber[]
  pic: string | null
  hodnota: string[]
  onZmena: (ids: string[]) => void
  onProhodit: () => void
  veVzduchu: Set<number>
  hledani: boolean
  maxPocet: number
}) {
  const data = osoby
    .filter((o) => !o.externi && String(o.id) !== pic)
    .sort((a, b) => jmeno(a).localeCompare(jmeno(b), 'cs'))
    .map((o) => ({
      value: String(o.id),
      label: jmeno(o) + (veVzduchu.has(o.id) ? ' – ✈ ve vzduchu' : ''),
    }))
  return (
    <Stack gap={6}>
      <MultiSelect
        label="Další členové aeroklubu na palubě"
        description="Spolucestující z klubu vyberte jménem."
        size="md"
        searchable={hledani}
        data={data}
        value={hodnota}
        onChange={onZmena}
        maxValues={Math.max(hodnota.length, maxPocet)}
        placeholder={hodnota.length === 0 ? 'Nikdo' : undefined}
        hidePickedOptions
      />
      {pic && hodnota.length === 1 && (
        <Button variant="light" size="sm" onClick={onProhodit}>
          ⇅ Prohodit role (PIC ↔ člen)
        </Button>
      )}
    </Stack>
  )
}
