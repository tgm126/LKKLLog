import { Card, Table, Text } from '@mantine/core'

import type { RadekSouhrnu } from '../api/vypis'
import { doba } from '../cas'

/** Dlaždice s jedním číslem souhrnu (lety, doba…). */
export function Dlazdice({ nazev, hodnota }: { nazev: string; hodnota: string | number }) {
  return (
    <Card withBorder padding="xs">
      <Text fz="xs" c="dimmed">
        {nazev}
      </Text>
      <Text fw={700} fz="xl">
        {hodnota}
      </Text>
    </Card>
  )
}

/** Tabulka součtů (podle letadel, plátců…) s řádkem Celkem. */
export function TabulkaSouhrnu({
  nadpis,
  radky,
  celkem,
}: {
  nadpis: string[]
  radky: { klic: string; bunky: string[]; hodnoty: RadekSouhrnu }[]
  celkem: RadekSouhrnu
}) {
  const cisla = (r: RadekSouhrnu) => [r.lety, doba(r.minuty), r.pristani ?? '–', r.navijak, r.vlek]
  return (
    <Table.ScrollContainer minWidth={520}>
      <Table striped withTableBorder fz="sm">
        <Table.Thead>
          <Table.Tr>
            {[...nadpis, 'Lety', 'Doba', 'Přistání', 'Naviják', 'Vleky'].map((n) => (
              <Table.Th key={n}>{n}</Table.Th>
            ))}
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {radky.map((r) => (
            <Table.Tr key={r.klic}>
              {[...r.bunky, ...cisla(r.hodnoty)].map((b, i) => (
                <Table.Td key={i}>{b}</Table.Td>
              ))}
            </Table.Tr>
          ))}
          <Table.Tr fw={700}>
            <Table.Td colSpan={nadpis.length}>Celkem</Table.Td>
            {cisla(celkem).map((b, i) => (
              <Table.Td key={i}>{b}</Table.Td>
            ))}
          </Table.Tr>
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  )
}
