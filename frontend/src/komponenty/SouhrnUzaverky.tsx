import { Group, SimpleGrid, Stack, Table, Text } from '@mantine/core'

import type { SouhrnUzaverky as Souhrn } from '../api/uzaverky'
import { doba } from '../cas'
import { useNazvy } from '../nazvy'
import { useCiselniky } from '../useLety'
import { Dlazdice, TabulkaSouhrnu } from './Souhrn'

/** Souhrn uzávěrky: celkem, starty, podle letadel; volitelně i podle plátců a osob. */
export function SouhrnUzaverky({ souhrn: s, uplny = false }: { souhrn: Souhrn; uplny?: boolean }) {
  const { data: c } = useCiselniky()
  const n = useNazvy(c)
  const starty = Object.entries(s.starty).filter(([, pocet]) => pocet > 0)
  return (
    <Stack gap="sm">
      <SimpleGrid cols={{ base: 3, sm: 4 }} spacing="xs">
        <Dlazdice nazev="Lety" hodnota={s.celkem.lety} />
        <Dlazdice nazev="Doba" hodnota={doba(s.celkem.minuty)} />
        <Dlazdice nazev="Přistání" hodnota={s.celkem.pristani ?? '–'} />
        <Dlazdice nazev="Vleky" hodnota={s.celkem.vlek} />
      </SimpleGrid>
      <Group gap="md">
        <Text fz="sm" c="dimmed">
          Starty:{' '}
          {starty.length === 0
            ? 'žádné'
            : starty.map(([z, pocet]) => `${n.zpusob(z).toLowerCase()} ${pocet}`).join(' · ')}
        </Text>
        {s.soukrome.lety > 0 && (
          <Text fz="sm" c="dimmed">
            Soukromá letadla (nepočítají se): {s.soukrome.lety}× {doba(s.soukrome.minuty)}
          </Text>
        )}
        {s.zruseno > 0 && (
          <Text fz="sm" c="dimmed">
            Zrušeno: {s.zruseno}
          </Text>
        )}
      </Group>
      {s.podle_letadel.length > 0 && (
        <TabulkaSouhrnu
          nadpis={['Letadlo', 'Účel']}
          radky={s.podle_letadel.map((r) => ({
            klic: `${r.imatrikulace}-${r.ucel}`,
            bunky: [r.imatrikulace, r.ucel],
            hodnoty: r,
          }))}
          celkem={s.celkem}
        />
      )}
      {uplny && s.podle_platcu.length > 0 && (
        <TabulkaSouhrnu
          nadpis={['Platí']}
          radky={s.podle_platcu.map((r) => ({ klic: r.platce, bunky: [r.platce], hodnoty: r }))}
          celkem={s.celkem}
        />
      )}
      {uplny && s.podle_osob.length > 0 && (
        <Table.ScrollContainer minWidth={360}>
          <Table striped withTableBorder fz="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Osoba</Table.Th>
                <Table.Th>Funkce</Table.Th>
                <Table.Th>Lety</Table.Th>
                <Table.Th>Doba</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {s.podle_osob.map((r) => (
                <Table.Tr key={`${r.osoba_id}-${r.funkce}`}>
                  <Table.Td>{r.osoba}</Table.Td>
                  <Table.Td>{r.funkce}</Table.Td>
                  <Table.Td>{r.lety}</Table.Td>
                  <Table.Td>{doba(r.minuty)}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      )}
    </Stack>
  )
}
