import {
  Alert,
  Button,
  Container,
  Group,
  Loader,
  SegmentedControl,
  SimpleGrid,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useState } from 'react'

import type { Let } from '../api/lety'
import { nactiNalet, odkazExportuNaletu, type RadekNaletu } from '../api/nalet'
import { doba, hhmm } from '../cas'
import { DetailLetu } from '../komponenty/DetailLetu'
import { OpravaLetu } from '../komponenty/OpravaLetu'
import { Dlazdice } from '../komponenty/Souhrn'
import { ZruseniDialog } from '../komponenty/ZruseniDialog'
import { KATEGORIE_LETU, useNazvy } from '../nazvy'
import { useCiselniky, useServerovyCas } from '../useLety'

const iso = (d: Date) => d.toISOString().slice(0, 10)

/** Období podle volby; „12“ a „24“ = posledních 12 / 24 měsíců (typické lhůty praxe). */
function obdobi(volba: string, vlastni: { od: string; do: string }) {
  const dnes = new Date()
  const zpet = (mesicu: number) =>
    iso(new Date(Date.UTC(dnes.getUTCFullYear(), dnes.getUTCMonth() - mesicu, dnes.getUTCDate() + 1)))
  if (volba === 'rok') return { od: `${dnes.getUTCFullYear()}-01-01`, do: iso(dnes) }
  if (volba === '12') return { od: zpet(12), do: iso(dnes) }
  if (volba === '24') return { od: zpet(24), do: iso(dnes) }
  return vlastni
}

function Tabulka({
  nadpis,
  radky,
}: {
  nadpis: string[]
  radky: { klic: string; bunky: string[]; hodnoty: RadekNaletu }[]
}) {
  return (
    <Table.ScrollContainer minWidth={320}>
      <Table striped withTableBorder fz="sm">
        <Table.Thead>
          <Table.Tr>
            {[...nadpis, 'Lety', 'Doba', 'Přistání'].map((n) => (
              <Table.Th key={n}>{n}</Table.Th>
            ))}
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {radky.map((r) => (
            <Table.Tr key={r.klic}>
              {r.bunky.map((b, i) => (
                <Table.Td key={i}>{b}</Table.Td>
              ))}
              <Table.Td>{r.hodnoty.lety}</Table.Td>
              <Table.Td fw={600}>{doba(r.hodnoty.minuty)}</Table.Td>
              <Table.Td>{r.hodnoty.pristani}</Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  )
}

/** Můj nálet: neoficiální osobní součty hodin a startů a seznam vlastních letů. */
export function MujNalet() {
  const { data: c } = useCiselniky()
  const n = useNazvy(c)
  const [volba, setVolba] = useState('rok')
  const [vlastni, setVlastni] = useState(() => obdobi('rok', { od: '', do: '' }))
  const { od, do: do_ } = obdobi(volba, vlastni)
  const nalet = useQuery({
    queryKey: ['nalet', od, do_],
    queryFn: () => nactiNalet(od, do_),
    placeholderData: keepPreviousData,
    enabled: !!od && !!do_,
  })
  const [detailId, setDetailId] = useState<number | null>(null)
  const [opravaId, setOpravaId] = useState<number | null>(null)
  const [zruseni, setZruseni] = useState<Let | null>(null)
  const ted = useServerovyCas(undefined)
  const data = nalet.data
  const s = data?.souhrn
  const detail = data?.lety.find((l) => l.id === detailId)
  const oprava = data?.lety.find((l) => l.id === opravaId)

  // Starty seskupené podle kategorie: „Plachtařské: naviják 12 · vlek 3“.
  const starty = Object.entries(
    (s?.starty ?? []).reduce<Record<string, string[]>>((vysledek, r) => {
      ;(vysledek[r.kategorie] ??= []).push(`${r.zpusob.toLowerCase()} ${r.pocet}`)
      return vysledek
    }, {}),
  )

  return (
    <Container size="md" pb="xl">
      <Stack gap="md">
        <div>
          <Title order={2}>Můj nálet</Title>
          <Text c="dimmed" fz="sm">
            Neoficiální přehled z evidence aeroklubu (lety ve funkci PIC, žák a přezkoušený, i na
            soukromých letadlech). Nenahrazuje zápisník letů.
          </Text>
        </div>

        <SegmentedControl
          value={volba}
          onChange={setVolba}
          data={[
            { value: 'rok', label: 'Tento rok' },
            { value: '12', label: '12 měsíců' },
            { value: '24', label: '24 měsíců' },
            { value: 'vlastni', label: 'Vlastní' },
          ]}
        />
        {volba === 'vlastni' && (
          <Group grow>
            <TextInput
              type="date"
              label="Od (UTC)"
              value={vlastni.od}
              onChange={(e) => setVlastni({ ...vlastni, od: e.currentTarget.value })}
            />
            <TextInput
              type="date"
              label="Do (UTC)"
              value={vlastni.do}
              onChange={(e) => setVlastni({ ...vlastni, do: e.currentTarget.value })}
            />
          </Group>
        )}

        {nalet.isError && <Alert color="red">{nalet.error.message}</Alert>}
        {nalet.isPending && <Loader />}
        {s && data && (
          <>
            <SimpleGrid cols={3} spacing="xs">
              <Dlazdice nazev="Lety" hodnota={s.celkem.lety} />
              <Dlazdice nazev="Doba" hodnota={doba(s.celkem.minuty)} />
              <Dlazdice nazev="Přistání" hodnota={s.celkem.pristani} />
            </SimpleGrid>
            {s.celkem.lety === 0 ? (
              <Text c="dimmed">V tomto období nemáte žádný ukončený let.</Text>
            ) : (
              <>
                <Title order={4}>Podle kategorie a funkce</Title>
                <Tabulka
                  nadpis={['Kategorie', 'Funkce']}
                  radky={s.podle_kategorie.map((r) => ({
                    klic: `${r.kategorie}-${r.funkce}`,
                    bunky: [r.kategorie, r.funkce],
                    hodnoty: r,
                  }))}
                />
                {starty.map(([kategorie, polozky]) => (
                  <Text key={kategorie} fz="sm">
                    <b>Starty – {kategorie.toLowerCase()}:</b> {polozky.join(' · ')}
                  </Text>
                ))}
                <Title order={4}>Podle účelu</Title>
                <Tabulka
                  nadpis={['Účel']}
                  radky={s.podle_ucelu.map((r) => ({ klic: r.ucel, bunky: [r.ucel], hodnoty: r }))}
                />
                <Group justify="space-between">
                  <Title order={4}>Moje lety ({data.lety.length})</Title>
                  <Button component="a" href={odkazExportuNaletu(od, do_)} variant="light" size="xs">
                    Stáhnout Excel
                  </Button>
                </Group>
                <Table.ScrollContainer minWidth={640}>
                  <Table striped highlightOnHover withTableBorder fz="sm">
                    <Table.Thead>
                      <Table.Tr>
                        <Table.Th>Datum</Table.Th>
                        <Table.Th>Letadlo</Table.Th>
                        <Table.Th>Funkce</Table.Th>
                        <Table.Th>Typ letu</Table.Th>
                        <Table.Th>Vzlet – přistání (UTC)</Table.Th>
                        <Table.Th>Doba</Table.Th>
                        <Table.Th>Přist.</Table.Th>
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {data.lety.map((l) => (
                        <Table.Tr key={l.id} onClick={() => setDetailId(l.id)} style={{ cursor: 'pointer' }}>
                          <Table.Td>
                            {l.cas_vzletu &&
                              new Date(l.cas_vzletu).toLocaleDateString('cs-CZ', { timeZone: 'UTC' })}
                          </Table.Td>
                          <Table.Td fw={600}>{l.imatrikulace}</Table.Td>
                          <Table.Td>{n.funkce(l.moje_funkce)}</Table.Td>
                          <Table.Td>
                            {KATEGORIE_LETU[l.kategorie]} · {n.ucel(l.ucel).toLowerCase()}
                          </Table.Td>
                          <Table.Td>
                            {l.misto_vzletu} {hhmm(l.cas_vzletu)} → {l.misto_pristani}{' '}
                            {hhmm(l.cas_pristani)}
                          </Table.Td>
                          <Table.Td fw={600}>{doba(l.doba_uctovana_min)}</Table.Td>
                          <Table.Td>{l.pocet_pristani}</Table.Td>
                        </Table.Tr>
                      ))}
                    </Table.Tbody>
                  </Table>
                </Table.ScrollContainer>
              </>
            )}
          </>
        )}
      </Stack>

      <DetailLetu
        let_={detail ?? null}
        onZavrit={() => setDetailId(null)}
        onOpravit={() => {
          setOpravaId(detailId)
          setDetailId(null)
        }}
        onZrusit={() => {
          setZruseni(detail ?? null)
          setDetailId(null)
        }}
      />
      {oprava && (
        <OpravaLetu
          key={`${oprava.id}-${oprava.verze}`}
          let_={oprava}
          lety={[]}
          ted={ted}
          onZavrit={() => setOpravaId(null)}
        />
      )}
      <ZruseniDialog let_={zruseni} onZavrit={() => setZruseni(null)} />
    </Container>
  )
}
