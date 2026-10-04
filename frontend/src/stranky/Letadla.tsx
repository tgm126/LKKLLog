import {
  Alert,
  Autocomplete,
  Button,
  Card,
  Container,
  Group,
  Loader,
  Modal,
  NumberInput,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import {
  type LetadloSprava,
  nactiLetadlaSprava,
  smazatTermin,
  type Termin,
  ulozitDenik,
  ulozitTermin,
} from '../api/licence'
import { doba } from '../cas'
import { BARVA_STAVU } from '../stav'

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

function SeznamLetadel() {
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
                <Text span c={BARVA_STAVU[t.stav]} fw={800}>
                  ●
                </Text>{' '}
                {t.nazev}
              </Text>
              <Text fz="sm" c={t.stav === 'ok' ? 'dimmed' : BARVA_STAVU[t.stav]} ta="right">
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

/** Letadla: nálet z deníku a evidence, termíny (admin, správce licencí a letadel). */
export function Letadla() {
  return (
    <Container size="lg" pb="xl">
      <Stack gap="sm">
        <Title order={3}>Letadla</Title>
        <SeznamLetadel />
      </Stack>
    </Container>
  )
}
