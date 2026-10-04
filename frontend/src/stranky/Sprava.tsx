import {
  Alert,
  Autocomplete,
  Badge,
  Button,
  Card,
  Container,
  Group,
  Loader,
  Modal,
  NumberInput,
  SegmentedControl,
  Stack,
  Switch,
  Text,
  TextInput,
  Title,
} from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router'

import {
  type Kontrola,
  type LetadloSprava,
  nactiLetadlaSprava,
  nactiPilota,
  nactiPiloty,
  type Pilot,
  smazatTermin,
  type Termin,
  ulozitDenik,
  ulozitTermin,
} from '../api/licence'
import { doba } from '../cas'
import { SeznamKontrol } from '../komponenty/Rozletanost'

const BARVA: Record<Kontrola['stav'], string> = { ok: 'green', pozor: 'orange', chyba: 'red', info: 'gray' }
const TEXT_STAVU: Record<Kontrola['stav'], string> = {
  ok: 'v pořádku',
  pozor: 'brzy vyprší',
  chyba: 'neplatné',
  info: 'info',
}
const BEZNE_TERMINY = [
  'ARC',
  'Roční prohlídka',
  '50h prohlídka',
  '100h prohlídka',
  'Pojištění',
  'Technický průkaz',
  'Generální oprava motoru (TBO)',
  'Vrtule',
  'Záchranný systém',
]

const datum = (iso: string | null) =>
  iso ? new Date(`${iso}T12:00:00Z`).toLocaleDateString('cs-CZ', { timeZone: 'UTC' }) : ''

function DetailPilota({ pilot, onZavrit }: { pilot: Pilot; onZavrit: () => void }) {
  const detail = useQuery({ queryKey: ['sprava', 'pilot', pilot.id], queryFn: () => nactiPilota(pilot.id) })
  return (
    <Modal opened onClose={onZavrit} title={pilot.jmeno} size="lg">
      <Stack gap="xs">
        {detail.isPending && <Loader size="sm" />}
        {detail.data && <SeznamKontrol kontroly={detail.data.kontroly} />}
        <Button component={Link} to={`/licence?osoba=${pilot.id}`} variant="light">
          Upravit licence a medical
        </Button>
      </Stack>
    </Modal>
  )
}

function Piloti() {
  const piloti = useQuery({ queryKey: ['sprava', 'piloti'], queryFn: nactiPiloty })
  const [jenProblemy, setJenProblemy] = useState(false)
  const [detail, setDetail] = useState<Pilot | null>(null)
  if (piloti.isPending) return <Loader />
  if (piloti.isError) return <Alert color="red">{piloti.error.message}</Alert>
  const seznam = piloti.data.filter((p) => !jenProblemy || p.stav === 'chyba' || p.stav === 'pozor')
  return (
    <Stack gap="xs">
      <Switch label="Jen piloti s problémem" checked={jenProblemy} onChange={(e) => setJenProblemy(e.currentTarget.checked)} />
      <Text fz="xs" c="dimmed">
        Piloti = aktivní členové s licencí nebo oprávněním. Stav počítá licence, medical a rozlétanost z
        letů v LKKL Log.
      </Text>
      {seznam.map((p) => (
        <Card
          key={p.id}
          withBorder
          padding="sm"
          onClick={() => setDetail(p)}
          style={{ cursor: 'pointer', borderLeft: `4px solid var(--mantine-color-${BARVA[p.stav]}-6)` }}
        >
          <Group justify="space-between" wrap="nowrap">
            <Text fw={700}>{p.jmeno}</Text>
            <Badge color={BARVA[p.stav]} variant="light">
              {TEXT_STAVU[p.stav]}
            </Badge>
          </Group>
          <Group gap={4} mt={4}>
            {p.licence.length === 0 && (
              <Text fz="sm" c="dimmed">
                bez licence
              </Text>
            )}
            {p.licence.map((l) => (
              <Badge key={l} variant="outline" color="gray">
                {l}
              </Badge>
            ))}
          </Group>
          {p.problemy.slice(0, 3).map((pr) => (
            <Text key={pr} fz="xs" c="dimmed">
              {pr}
            </Text>
          ))}
          {p.problemy.length > 3 && (
            <Text fz="xs" c="dimmed">
              … a další ({p.problemy.length - 3})
            </Text>
          )}
        </Card>
      ))}
      {detail && <DetailPilota pilot={detail} onZavrit={() => setDetail(null)} />}
    </Stack>
  )
}

function useUlozeniLetadel<T>(fn: (data: T) => Promise<LetadloSprava[]>, zprava: string, hotovo: () => void) {
  const klient = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: (letadla) => {
      klient.setQueryData(['sprava', 'letadla'], letadla)
      notifications.show({ message: zprava, color: 'green' })
      hotovo()
    },
    onError: (e) => notifications.show({ message: e.message, color: 'red' }),
  })
}

function DenikDialog({ letadlo, onZavrit }: { letadlo: LetadloSprava; onZavrit: () => void }) {
  const [hodiny, setHodiny] = useState<number | string>(Math.floor(letadlo.nalet_pocatek_min / 60))
  const [minuty, setMinuty] = useState<number | string>(letadlo.nalet_pocatek_min % 60)
  const [starty, setStarty] = useState<number | string>(letadlo.starty_pocatek)
  const [k, setK] = useState(letadlo.stav_k ?? '')
  const ulozeni = useUlozeniLetadel(
    () =>
      ulozitDenik(letadlo.id, {
        nalet_pocatek_min: Number(hodiny || 0) * 60 + Number(minuty || 0),
        starty_pocatek: Number(starty || 0),
        stav_k: k || null,
      }),
    'Stav deníku uložen.',
    onZavrit,
  )
  return (
    <Modal opened onClose={onZavrit} title={`${letadlo.imatrikulace} – stav provozního deníku`} centered>
      <Stack>
        <Text fz="sm" c="dimmed">
          Celkový nálet a starty letadla z provozního deníku k danému dni. Lety po tomto dni aplikace
          přičítá z evidence.
        </Text>
        <TextInput type="date" label="Stav ke dni" value={k} onChange={(e) => setK(e.currentTarget.value)} />
        <Group grow>
          <NumberInput label="Nálet – hodiny" min={0} value={hodiny} onChange={setHodiny} />
          <NumberInput label="minuty" min={0} max={59} value={minuty} onChange={setMinuty} />
        </Group>
        <NumberInput label="Starty celkem" min={0} value={starty} onChange={setStarty} />
        <Button loading={ulozeni.isPending} onClick={() => ulozeni.mutate(undefined)}>
          Uložit
        </Button>
      </Stack>
    </Modal>
  )
}

function TerminDialog({
  letadlo,
  termin,
  onZavrit,
}: {
  letadlo: LetadloSprava
  termin: Termin | null
  onZavrit: () => void
}) {
  const [nazev, setNazev] = useState(termin?.nazev ?? '')
  const [datumTerminu, setDatum] = useState(termin?.datum ?? '')
  const [hodiny, setHodiny] = useState<number | string>(termin?.pri_naletu_h ?? '')
  const [poznamka, setPoznamka] = useState(termin?.poznamka ?? '')
  const ulozeni = useUlozeniLetadel(
    () =>
      ulozitTermin({
        id: termin?.id,
        letadlo_id: letadlo.id,
        nazev,
        datum: datumTerminu || null,
        pri_naletu_h: hodiny === '' ? null : Number(hodiny),
        poznamka,
      }),
    'Termín uložen.',
    onZavrit,
  )
  const smazani = useUlozeniLetadel(() => smazatTermin(termin!.id), 'Termín smazán.', onZavrit)
  return (
    <Modal opened onClose={onZavrit} title={`${letadlo.imatrikulace} – ${termin ? 'termín' : 'nový termín'}`} centered>
      <Stack>
        <Autocomplete label="Název" data={BEZNE_TERMINY} value={nazev} onChange={setNazev} />
        <TextInput type="date" label="Do data" value={datumTerminu} onChange={(e) => setDatum(e.currentTarget.value)} />
        <NumberInput
          label="Nebo při celkovém náletu [h]"
          description={`Teď má letadlo nalétáno ${doba(letadlo.nalet_min)}.`}
          min={0}
          value={hodiny}
          onChange={setHodiny}
        />
        <TextInput label="Poznámka (nepovinné)" value={poznamka} onChange={(e) => setPoznamka(e.currentTarget.value)} />
        <Text fz="xs" c="dimmed">
          Stačí datum, nebo nálet; při obou platí, co nastane dřív.
        </Text>
        <Group justify="space-between">
          {termin ? (
            <Button variant="subtle" color="red" loading={smazani.isPending} onClick={() => smazani.mutate(undefined)}>
              Smazat
            </Button>
          ) : (
            <span />
          )}
          <Button
            disabled={!nazev.trim() || (!datumTerminu && hodiny === '')}
            loading={ulozeni.isPending}
            onClick={() => ulozeni.mutate(undefined)}
          >
            Uložit
          </Button>
        </Group>
      </Stack>
    </Modal>
  )
}

function Letadla() {
  const letadla = useQuery({ queryKey: ['sprava', 'letadla'], queryFn: nactiLetadlaSprava })
  const [denik, setDenik] = useState<LetadloSprava | null>(null)
  const [termin, setTermin] = useState<{ letadlo: LetadloSprava; termin: Termin | null } | null>(null)
  if (letadla.isPending) return <Loader />
  if (letadla.isError) return <Alert color="red">{letadla.error.message}</Alert>
  return (
    <Stack gap="xs">
      {letadla.data.map((l) => (
        <Card key={l.id} withBorder padding="sm">
          <Group justify="space-between" wrap="nowrap" align="flex-start">
            <div>
              <Group gap="xs">
                <Text fw={700}>{l.imatrikulace}</Text>
                <Text fz="sm" c="dimmed">
                  {l.typ}
                </Text>
              </Group>
              <Text fz="sm">
                Nálet {doba(l.nalet_min)} · {l.starty} startů
              </Text>
              {l.chybi_denik ? (
                <Text fz="xs" c="orange">
                  Chybí stav provozního deníku – zadejte ho při spuštění ostrého provozu, jinak nálet
                  a termíny podle náletu nesedí.
                </Text>
              ) : (
                <Text fz="xs" c="dimmed">
                  Stav deníku k {datum(l.stav_k)} + lety z evidence
                </Text>
              )}
            </div>
            <Stack gap={4}>
              <Button size="xs" variant="light" onClick={() => setTermin({ letadlo: l, termin: null })}>
                + Termín
              </Button>
              <Button size="xs" variant="default" onClick={() => setDenik(l)}>
                Stav deníku
              </Button>
            </Stack>
          </Group>
          {l.terminy.map((t) => (
            <Group
              key={t.id}
              justify="space-between"
              wrap="nowrap"
              mt={6}
              onClick={() => setTermin({ letadlo: l, termin: t })}
              style={{ cursor: 'pointer' }}
            >
              <Text fz="sm">
                <Text span c={BARVA[t.stav]} fw={800}>
                  ●
                </Text>{' '}
                {t.nazev}
              </Text>
              <Text fz="sm" c={t.stav === 'ok' ? 'dimmed' : BARVA[t.stav]} ta="right">
                {t.text}
              </Text>
            </Group>
          ))}
        </Card>
      ))}
      {denik && <DenikDialog letadlo={denik} onZavrit={() => setDenik(null)} />}
      {termin && <TerminDialog letadlo={termin.letadlo} termin={termin.termin} onZavrit={() => setTermin(null)} />}
    </Stack>
  )
}

/** Piloti a letadla: přehled pro správce licencí a letadel (a admina). */
export function Sprava() {
  const [pohled, setPohled] = useState('piloti')
  return (
    <Container size="sm" pb="xl">
      <Stack gap="md">
        <Title order={2}>Piloti a letadla</Title>
        <SegmentedControl
          value={pohled}
          onChange={setPohled}
          data={[
            { value: 'piloti', label: 'Piloti' },
            { value: 'letadla', label: 'Letadla' },
          ]}
        />
        {pohled === 'piloti' ? <Piloti /> : <Letadla />}
      </Stack>
    </Container>
  )
}
