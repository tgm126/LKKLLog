import {
  Alert,
  Button,
  Collapse,
  Container,
  Group,
  Loader,
  SegmentedControl,
  Select,
  SimpleGrid,
  Stack,
  Switch,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core'
import { useDisclosure, useMediaQuery } from '@mantine/hooks'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useState } from 'react'

import type { Let } from '../api/lety'
import { type FiltrVypisu, nactiVypis, odkazExportu } from '../api/vypis'
import { doba, hhmm } from '../cas'
import { DetailLetu } from '../komponenty/DetailLetu'
import { Dlazdice, TabulkaSouhrnu } from '../komponenty/Souhrn'
import { OpravaLetu } from '../komponenty/OpravaLetu'
import { ZruseniDialog } from '../komponenty/ZruseniDialog'
import { KATEGORIE_LETU, useNazvy } from '../nazvy'
import { jmeno } from '../posadka'
import { useCiselniky, useServerovyCas } from '../useLety'

const iso = (d: Date) => d.toISOString().slice(0, 10)

function obdobi(volba: string, vlastni: { od: string; do: string }) {
  const dnes = new Date()
  const prvni = new Date(Date.UTC(dnes.getUTCFullYear(), dnes.getUTCMonth(), 1))
  if (volba === 'tento') return { od: iso(prvni), do: iso(dnes) }
  if (volba === 'minuly') {
    const konec = new Date(prvni.getTime() - 86_400_000)
    return { od: iso(new Date(Date.UTC(konec.getUTCFullYear(), konec.getUTCMonth(), 1))), do: iso(konec) }
  }
  return vlastni
}

export function Vypis() {
  const { data: c } = useCiselniky()
  const n = useNazvy(c)
  const mobil = useMediaQuery('(max-width: 48em)')
  const [filtryOtevrene, filtry] = useDisclosure(!mobil)
  const [volbaObdobi, setVolbaObdobi] = useState('tento')
  const [vlastni, setVlastni] = useState(() => obdobi('tento', { od: '', do: '' }))
  const [f, setF] = useState<Omit<FiltrVypisu, 'od' | 'do'>>({ soukrome: false, zrusene: false })
  const filtr: FiltrVypisu = { ...obdobi(volbaObdobi, vlastni), ...f }
  const vypis = useQuery({
    queryKey: ['vypis', filtr],
    queryFn: () => nactiVypis(filtr),
    placeholderData: keepPreviousData,
  })
  const [detailId, setDetailId] = useState<number | null>(null)
  const [opravaId, setOpravaId] = useState<number | null>(null)
  const [zruseni, setZruseni] = useState<Let | null>(null)
  const nastav = (klic: keyof typeof f) => (v: string | null) => setF({ ...f, [klic]: v })

  const osoby = (c?.osoby ?? [])
    .slice()
    .sort((a, b) => jmeno(a).localeCompare(jmeno(b), 'cs'))
    .map((o) => ({ value: String(o.id), label: jmeno(o) }))
  const detail = vypis.data?.lety.find((l) => l.id === detailId)
  const oprava = vypis.data?.lety.find((l) => l.id === opravaId)
  const data = vypis.data
  const s = data?.souhrn
  const ted = useServerovyCas(undefined)

  return (
    <Container size="lg" pb="xl">
      <Stack gap="md">
        <Group justify="space-between">
          <Title order={2}>Výpis letů</Title>
          {vypis.data?.smi_exportovat && (
            <Group gap="xs">
              <Button component="a" href={odkazExportu('xlsx', filtr)} variant="light">
                Stáhnout Excel
              </Button>
              <Button component="a" href={odkazExportu('csv', filtr)} variant="subtle">
                CSV
              </Button>
            </Group>
          )}
        </Group>

        <SegmentedControl
          value={volbaObdobi}
          onChange={setVolbaObdobi}
          data={[
            { value: 'tento', label: 'Tento měsíc' },
            { value: 'minuly', label: 'Minulý měsíc' },
            { value: 'vlastni', label: 'Vlastní' },
          ]}
        />
        {volbaObdobi === 'vlastni' && (
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

        <Button variant="subtle" onClick={filtry.toggle} style={{ alignSelf: 'flex-start' }}>
          {filtryOtevrene ? 'Skrýt filtry' : 'Filtry…'}
        </Button>
        <Collapse expanded={filtryOtevrene}>
          <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="xs">
            <Select
              label="Letadlo"
              clearable
              placeholder="Všechna"
              data={(c?.letadla ?? []).map((l) => ({ value: String(l.id), label: l.imatrikulace }))}
              value={f.letadlo ?? null}
              onChange={nastav('letadlo')}
            />
            <Select
              label="Osoba v posádce"
              clearable
              searchable={!mobil}
              placeholder="Kdokoli"
              data={osoby}
              value={f.osoba ?? null}
              onChange={nastav('osoba')}
            />
            <Select
              label="Platí"
              clearable
              searchable={!mobil}
              placeholder="Kdokoli"
              data={[{ value: '0', label: 'Aeroklub' }, ...osoby]}
              value={f.platce ?? null}
              onChange={nastav('platce')}
            />
            <Select
              label="Kategorie"
              clearable
              placeholder="Všechny"
              data={(c?.kategorie ?? []).map((k) => ({ value: k.hodnota, label: k.nazev }))}
              value={f.kategorie ?? null}
              onChange={nastav('kategorie')}
            />
            <Select
              label="Účel"
              clearable
              placeholder="Všechny"
              data={(c?.ucely ?? []).map((u) => ({ value: u.hodnota, label: u.nazev }))}
              value={f.ucel ?? null}
              onChange={nastav('ucel')}
            />
            <Select
              label="Způsob vzletu"
              clearable
              placeholder="Všechny"
              data={(c?.zpusoby_vzletu ?? []).map((z) => ({ value: z.hodnota, label: z.nazev }))}
              value={f.zpusob ?? null}
              onChange={nastav('zpusob')}
            />
          </SimpleGrid>
          <Group mt="sm">
            <Switch
              label="Včetně soukromých letadel"
              checked={f.soukrome}
              onChange={(e) => setF({ ...f, soukrome: e.currentTarget.checked })}
            />
            <Switch
              label="Včetně zrušených letů"
              checked={f.zrusene}
              onChange={(e) => setF({ ...f, zrusene: e.currentTarget.checked })}
            />
          </Group>
        </Collapse>

        {vypis.isError && <Alert color="red">{vypis.error.message}</Alert>}
        {vypis.isPending && <Loader />}
        {s && data && (
          <>
            <SimpleGrid cols={{ base: 2, sm: 5 }} spacing="xs">
              <Dlazdice nazev="Lety" hodnota={s.celkem.lety} />
              <Dlazdice nazev="Doba" hodnota={doba(s.celkem.minuty)} />
              <Dlazdice nazev="T&G" hodnota={s.celkem.tg} />
              <Dlazdice nazev="Starty navijákem" hodnota={s.celkem.navijak} />
              <Dlazdice nazev="Vleky" hodnota={s.celkem.vlek} />
            </SimpleGrid>
            {(s.neukonceno > 0 || s.zruseno > 0) && (
              <Text fz="sm" c="dimmed">
                Počítají se jen ukončené lety.
                {s.neukonceno > 0 && ` Neukončené v období: ${s.neukonceno}.`}
                {s.zruseno > 0 && ` Zrušené: ${s.zruseno}.`}
              </Text>
            )}
            <Title order={4}>Podle letadel</Title>
            <TabulkaSouhrnu
              nadpis={['Letadlo', 'Účel']}
              radky={s.podle_letadel.map((r) => ({
                klic: `${r.imatrikulace}-${r.ucel}`,
                bunky: [r.imatrikulace, r.ucel],
                hodnoty: r,
              }))}
              celkem={s.celkem}
            />
            <Title order={4}>Podle plátců</Title>
            <TabulkaSouhrnu
              nadpis={['Platí']}
              radky={s.podle_platcu.map((r) => ({ klic: r.platce, bunky: [r.platce], hodnoty: r }))}
              celkem={s.celkem}
            />
            <Title order={4}>Lety ({data.lety.length})</Title>
            <Table.ScrollContainer minWidth={760}>
              <Table striped highlightOnHover withTableBorder fz="sm">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Datum</Table.Th>
                    <Table.Th>Letadlo</Table.Th>
                    <Table.Th>Typ letu</Table.Th>
                    <Table.Th>PIC</Table.Th>
                    <Table.Th>Platí</Table.Th>
                    <Table.Th>Vzlet – přistání (UTC)</Table.Th>
                    <Table.Th>Doba</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {data.lety.map((l) => (
                    <Table.Tr
                      key={l.id}
                      onClick={() => setDetailId(l.id)}
                      style={{
                        cursor: 'pointer',
                        textDecoration: l.stav === 'zrusen' ? 'line-through' : undefined,
                      }}
                    >
                      <Table.Td>
                        {l.cas_vzletu &&
                          new Date(l.cas_vzletu).toLocaleDateString('cs-CZ', { timeZone: 'UTC' })}
                      </Table.Td>
                      <Table.Td fw={600}>{l.imatrikulace}</Table.Td>
                      <Table.Td>
                        {KATEGORIE_LETU[l.kategorie]} · {n.ucel(l.ucel).toLowerCase()}
                      </Table.Td>
                      <Table.Td>{l.posadka.find((p) => p.funkce === 'pic')?.jmeno}</Table.Td>
                      <Table.Td>{l.plati_aeroklub ? 'Aeroklub' : l.platce}</Table.Td>
                      <Table.Td>
                        {l.misto_vzletu} {hhmm(l.cas_vzletu)}
                        {l.cas_pristani ? ` → ${l.misto_pristani} ${hhmm(l.cas_pristani)}` : ' → letí'}
                      </Table.Td>
                      <Table.Td fw={600}>{doba(l.doba_uctovana_min)}</Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Table.ScrollContainer>
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
