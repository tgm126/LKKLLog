import {
  Alert,
  Badge,
  Button,
  Group,
  Modal,
  SegmentedControl,
  Select,
  SimpleGrid,
  Stack,
  Stepper,
  Text,
  UnstyledButton,
} from '@mantine/core'
import { useMediaQuery } from '@mantine/hooks'
import { notifications } from '@mantine/notifications'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'

import { type Let, type NovyLet as NovyLetData, type OsobaVyber, zalozitLet } from '../api/lety'
import { KATEGORIE_LETU } from '../nazvy'
import { PREHLED_KLIC, useCiselniky } from '../useLety'
import { naMinuty } from '../cas'
import { CasVolba } from './CasVolba'
import { Pocitadlo } from './Pocitadlo'

const UROVEN: Record<string, number> = { zak: 0, pilot: 1, instruktor: 2, examinator: 3 }

type Slot = { funkce: string; popis: string; min: number; max: number }

/** Políčka posádky podle účelu letu (kap. 3.1 návrhu). */
const SLOTY: Record<string, { pic: Slot; druhy: Slot | null }> = {
  normalni: { pic: { funkce: 'pic', popis: 'PIC', min: 1, max: 3 }, druhy: null },
  vycvik: {
    pic: { funkce: 'pic', popis: 'Instruktor (PIC)', min: 2, max: 3 },
    druhy: { funkce: 'zak', popis: 'Žák', min: 0, max: 0 },
  },
  vycvik_solo: {
    pic: { funkce: 'pic', popis: 'Žák (PIC)', min: 0, max: 0 },
    druhy: { funkce: 'dozor', popis: 'Dozorující instruktor (na zemi)', min: 2, max: 3 },
  },
  prezkouseni: {
    pic: { funkce: 'pic', popis: 'Examinátor / instruktor (PIC)', min: 2, max: 3 },
    druhy: { funkce: 'prezkouseny', popis: 'Přezkoušený pilot', min: 0, max: 3 },
  },
}

const UCELY = [
  { hodnota: 'normalni', nazev: 'Normální' },
  { hodnota: 'vycvik', nazev: 'Výcvik' },
  { hodnota: 'vycvik_solo', nazev: 'Výcvik sólo' },
  { hodnota: 'prezkouseni', nazev: 'Přezkoušení' },
]

const KROKY = ['Letadlo', 'Účel', 'Posádka', 'Úloha', 'Vzlet']

const jmeno = (o: OsobaVyber) => `${o.prijmeni} ${o.jmeno}`

/** Nabídka osob: nahoře ti s odpovídajícím oprávněním, pak ostatní. */
function nabidka(
  osoby: OsobaVyber[],
  kategorie: string,
  slot: Slot,
  externiSmi: boolean,
  veVzduchu: Set<number>,
) {
  const uroven = (o: OsobaVyber) =>
    Math.max(-1, ...o.opravneni.filter((op) => op.kategorie === kategorie).map((op) => UROVEN[op.uroven]))
  const vhodne = osoby.filter((o) => externiSmi || !o.externi)
  const doporuceni = vhodne
    .filter((o) => uroven(o) >= slot.min && uroven(o) <= slot.max)
    .sort((a, b) => uroven(b) - uroven(a) || jmeno(a).localeCompare(jmeno(b), 'cs'))
  const ostatni = vhodne.filter((o) => !doporuceni.includes(o))
  const polozky = (seznam: OsobaVyber[]) =>
    seznam.map((o) => ({
      value: String(o.id),
      label:
        jmeno(o) + (o.externi ? ' (externí)' : '') + (veVzduchu.has(o.id) ? ' – ✈ ve vzduchu' : ''),
    }))
  return [
    { group: 'Doporučení', items: polozky(doporuceni) },
    { group: 'Ostatní', items: polozky(ostatni) },
  ].filter((g) => g.items.length > 0)
}

export function NovyLet({
  otevreno,
  onZavrit,
  lety,
  ted,
}: {
  otevreno: boolean
  onZavrit: () => void
  lety: Let[]
  ted: Date
}) {
  const { data: c } = useCiselniky()
  const mobil = useMediaQuery('(max-width: 48em)')
  // Na dotykových zařízeních bez vyhledávání – jinak by vyskočila klávesnice.
  const hledani = useMediaQuery('(pointer: fine)') ?? true
  const klient = useQueryClient()

  const [krok, setKrok] = useState(0)
  const [letadloId, setLetadloId] = useState<number | null>(null)
  const [ucel, setUcel] = useState('normalni')
  const [pic, setPic] = useState<string | null>(null)
  const [druhy, setDruhy] = useState<string | null>(null)
  const [hoste, setHoste] = useState(0)
  const [platce, setPlatce] = useState<string | null>(null) // null = podle pravidla
  const [ulohaId, setUlohaId] = useState<string | null>(null)
  const [zpusob, setZpusob] = useState('navijak')
  const [mistoVzletu, setMistoVzletu] = useState<string | null>(null)
  const [rezim, setRezim] = useState<'ted' | 'cas' | 'dopsat' | null>(null)
  const [casVzletu, setCasVzletu] = useState(() => naMinuty(new Date()))
  const [casPristani, setCasPristani] = useState(() => naMinuty(new Date()))
  const [mistoPristani, setMistoPristani] = useState<string | null>(null)
  const [tg, setTg] = useState(0)
  const [kratky, setKratky] = useState('start_bez_doby')

  const letadlo = c?.letadla.find((l) => l.id === letadloId)
  const sloty = SLOTY[ucel]
  const domovske = c?.letiste.find((l) => l.domovske)

  const zavrit = () => {
    setKrok(0)
    setLetadloId(null)
    setUcel('normalni')
    setPic(null)
    setDruhy(null)
    setHoste(0)
    setPlatce(null)
    setUlohaId(null)
    setMistoVzletu(null)
    setRezim(null)
    setTg(0)
    onZavrit()
  }

  // Kdo právě letí (dozor na zemi se nepočítá) – server mu druhý vzlet nedovolí.
  const veVzduchu = new Set(
    lety
      .filter((l) => l.stav === 've_vzduchu')
      .flatMap((l) => l.posadka.filter((p) => p.funkce !== 'dozor').map((p) => p.osoba_id)),
  )

  const stavLetadla = (id: number) =>
    lety.find((l) => l.letadlo_id === id && (l.stav === 've_vzduchu' || l.stav === 'pripraven'))
      ?.stav

  const posadka = useMemo(() => {
    const p: { osoba_id: number; funkce: string }[] = []
    if (pic) p.push({ osoba_id: Number(pic), funkce: 'pic' })
    if (druhy && sloty.druhy) p.push({ osoba_id: Number(druhy), funkce: sloty.druhy.funkce })
    return p
  }, [pic, druhy, sloty])

  // Výchozí plátce: výcvik žák, přezkoušení přezkoušený, jinak PIC (sólo = žák jako PIC).
  const vychoziPlatce =
    ucel === 'vycvik' || ucel === 'prezkouseni' ? druhy : pic
  const platceVyber = platce ?? vychoziPlatce
  const moznostiPlatce = (c?.osoby ?? [])
    .filter((o) => posadka.some((p) => p.osoba_id === o.id && p.funkce !== 'dozor') && !o.externi)
    .map((o) => ({ value: String(o.id), label: jmeno(o) }))

  const ulohy = (c?.osnovy ?? [])
    .filter((o) => o.kategorie === letadlo?.kategorie)
    .map((o) => ({
      group: o.nazev,
      items: o.ulohy
        .filter((u) => u.ucely.includes(ucel))
        .map((u) => ({ value: String(u.id), label: `${u.kod} – ${u.nazev}` })),
    }))
    .filter((g) => g.items.length > 0)

  const kratkyDopsany =
    rezim === 'dopsat' && casPristani.getTime() - casVzletu.getTime() < 60_000

  const zalozeni = useMutation({
    mutationFn: (akce: 'pripravit' | 'vzlet' | 'dopsat') => {
      const data: NovyLetData = {
        letadlo_id: letadloId!,
        ucel,
        posadka,
        uloha_id: ulohaId ? Number(ulohaId) : null,
        zpusob_vzletu: letadlo?.kategorie === 'kluzak' ? zpusob : 'vlastni',
        misto_vzletu_id: mistoVzletu ? Number(mistoVzletu) : null,
        pocet_hostu: ucel === 'normalni' ? hoste : 0,
        platce_id: platceVyber && platceVyber !== 'aeroklub' ? Number(platceVyber) : null,
        plati_aeroklub: platceVyber === 'aeroklub',
        akce,
      }
      if (akce === 'vzlet' && rezim === 'cas') data.cas_vzletu = casVzletu.toISOString()
      if (akce === 'dopsat') {
        data.cas_vzletu = casVzletu.toISOString()
        data.cas_pristani = casPristani.toISOString()
        data.misto_pristani_id = mistoPristani ? Number(mistoPristani) : null
        data.pocet_tg = tg
        if (kratkyDopsany) data.kratky_let = kratky
      }
      return zalozitLet(data)
    },
    onSuccess: (l, akce) => {
      const co = { pripravit: 'připraven', vzlet: 've vzduchu', dopsat: 'zapsán' }[akce]
      notifications.show({ message: `Let ${l.imatrikulace} ${co}.`, color: 'green' })
      void klient.invalidateQueries({ queryKey: PREHLED_KLIC })
      zavrit()
    },
    onError: (e) => notifications.show({ message: e.message, color: 'red', autoClose: 8000 }),
  })

  const muzeDal = [
    letadloId !== null,
    true,
    pic !== null && (!sloty.druhy || druhy !== null),
    true,
  ][krok]

  const letisteData = (c?.letiste ?? []).map((l) => ({
    value: String(l.id),
    label: l.icao ? `${l.icao} ${l.nazev}` : l.nazev,
  }))

  return (
    <Modal opened={otevreno} onClose={zavrit} title="Nový let" fullScreen={mobil} size="lg">
      {mobil ? (
        <Text fw={600} mb="md">
          Krok {krok + 1}/5: {KROKY[krok]}
          {letadlo && krok > 0 && (
            <Text span c="dimmed" fw={400}>
              {' '}
              · {letadlo.imatrikulace}
            </Text>
          )}
        </Text>
      ) : (
        <Stepper active={krok} onStepClick={(k) => k < krok && setKrok(k)} size="xs" mb="md">
          {KROKY.map((k) => (
            <Stepper.Step key={k} label={k} />
          ))}
        </Stepper>
      )}

      {krok === 0 && (
        <SimpleGrid cols={{ base: 2, sm: 3 }} spacing="xs">
          {(c?.letadla ?? []).map((l) => {
            const stav = stavLetadla(l.id)
            const vybrano = l.id === letadloId
            return (
              <UnstyledButton
                key={l.id}
                disabled={stav === 've_vzduchu'}
                onClick={() => {
                  setLetadloId(l.id)
                  setUlohaId(null)
                  setKrok(1)
                }}
                p="sm"
                style={{
                  border: `2px solid var(--mantine-color-${vybrano ? 'blue-6' : 'default-border'})`,
                  borderRadius: 8,
                  opacity: stav === 've_vzduchu' ? 0.45 : 1,
                }}
              >
                <Text fw={700}>{l.imatrikulace}</Text>
                <Text fz="xs" c="dimmed" lineClamp={1}>
                  {l.typ}
                </Text>
                <Group gap={4} mt={4}>
                  <Badge size="xs" variant="light">
                    {KATEGORIE_LETU[l.kategorie]}
                  </Badge>
                  {l.soukrome && (
                    <Badge size="xs" color="gray">
                      soukromé
                    </Badge>
                  )}
                  {stav === 've_vzduchu' && (
                    <Badge size="xs" color="green">
                      ve vzduchu
                    </Badge>
                  )}
                  {stav === 'pripraven' && (
                    <Badge size="xs" color="yellow">
                      připraven
                    </Badge>
                  )}
                </Group>
              </UnstyledButton>
            )
          })}
        </SimpleGrid>
      )}

      {krok === 1 && (
        <Stack>
          {letadlo && stavLetadla(letadlo.id) === 'pripraven' && (
            <Alert color="yellow">
              Pro {letadlo.imatrikulace} už je jeden let připravený. Nezakládáte ho podruhé?
            </Alert>
          )}
          <SimpleGrid cols={2} spacing="xs">
            {UCELY.map((u) => (
              <Button
                key={u.hodnota}
                size="lg"
                variant={u.hodnota === ucel ? 'filled' : 'default'}
                onClick={() => {
                  setUcel(u.hodnota)
                  setPic(null)
                  setDruhy(null)
                  setPlatce(null)
                  setUlohaId(null)
                  setKrok(2)
                }}
              >
                {u.nazev}
              </Button>
            ))}
          </SimpleGrid>
        </Stack>
      )}

      {krok === 2 && letadlo && c && (
        <Stack>
          <Select
            label={sloty.pic.popis}
            size="md"
            searchable={hledani}
            data={nabidka(c.osoby, letadlo.kategorie, sloty.pic, ucel === 'prezkouseni', veVzduchu)}
            value={pic}
            onChange={(v) => {
              setPic(v)
              setPlatce(null)
            }}
            nothingFoundMessage="Nikdo takový"
          />
          {sloty.druhy && (
            <Select
              label={sloty.druhy.popis}
              size="md"
              searchable={hledani}
              data={nabidka(
                c.osoby.filter((o) => String(o.id) !== pic),
                letadlo.kategorie,
                sloty.druhy,
                false,
                veVzduchu,
              )}
              value={druhy}
              onChange={(v) => {
                setDruhy(v)
                setPlatce(null)
              }}
            />
          )}
          {ucel === 'normalni' && (
            <Pocitadlo
              popis="Hosté mimo klub (počet)"
              hodnota={hoste}
              onZmena={setHoste}
              max={Math.max(0, letadlo.pocet_mist - 1)}
            />
          )}
          <Select
            label="Platí"
            size="md"
            data={[...moznostiPlatce, { value: 'aeroklub', label: 'Aeroklub' }]}
            value={platceVyber}
            onChange={setPlatce}
            allowDeselect={false}
            description="Předvyplněno podle účelu letu, lze změnit."
          />
        </Stack>
      )}

      {krok === 3 && letadlo && (
        <Stack>
          <Select
            label="Úloha"
            size="md"
            searchable={hledani}
            clearable
            placeholder="Bez úlohy"
            data={ulohy}
            value={ulohaId}
            onChange={setUlohaId}
            nothingFoundMessage="Pro tento účel nejsou úlohy"
          />
          {letadlo.kategorie === 'kluzak' && (
            <Stack gap={4}>
              <Text fz="sm" fw={500}>
                Způsob vzletu
              </Text>
              <SegmentedControl
                size="md"
                value={zpusob}
                onChange={setZpusob}
                data={[
                  { value: 'navijak', label: 'Naviják' },
                  { value: 'autostart', label: 'Autostart' },
                  { value: 'vlek', label: 'Vlek (brzy)', disabled: true },
                ]}
              />
            </Stack>
          )}
          <Select
            label="Místo vzletu"
            size="md"
            data={letisteData}
            value={mistoVzletu ?? (domovske ? String(domovske.id) : null)}
            onChange={setMistoVzletu}
            allowDeselect={false}
          />
        </Stack>
      )}

      {krok === 4 && (
        <Stack>
          {rezim === null && (
            <>
              <Button
                size="xl"
                color="blue"
                loading={zalozeni.isPending}
                onClick={() => zalozeni.mutate('vzlet')}
              >
                VZLET TEĎ
              </Button>
              <Button
                size="lg"
                variant="default"
                loading={zalozeni.isPending}
                onClick={() => zalozeni.mutate('pripravit')}
              >
                Připravit (vzlet zmáčknu později)
              </Button>
              <Button size="lg" variant="default" onClick={() => setRezim('cas')}>
                Vzlet byl v…
              </Button>
              <Button size="lg" variant="default" onClick={() => setRezim('dopsat')}>
                Dopsat proběhlý let
              </Button>
            </>
          )}
          {rezim === 'cas' && (
            <>
              <CasVolba popis="Čas vzletu (UTC)" hodnota={casVzletu} onZmena={setCasVzletu} ted={ted} />
              <Button size="lg" loading={zalozeni.isPending} onClick={() => zalozeni.mutate('vzlet')}>
                Zapsat vzlet
              </Button>
              <Button variant="subtle" onClick={() => setRezim(null)}>
                Zpět
              </Button>
            </>
          )}
          {rezim === 'dopsat' && (
            <>
              <CasVolba popis="Vzlet (UTC)" hodnota={casVzletu} onZmena={setCasVzletu} ted={ted} />
              <CasVolba
                popis="Přistání (UTC)"
                hodnota={casPristani}
                onZmena={setCasPristani}
                ted={ted}
              />
              <Select
                label="Místo přistání"
                size="md"
                data={letisteData}
                value={mistoPristani ?? (domovske ? String(domovske.id) : null)}
                onChange={setMistoPristani}
                allowDeselect={false}
              />
              <Pocitadlo popis="Touch-and-go" hodnota={tg} onZmena={setTg} />
              {kratkyDopsany && casPristani >= casVzletu && (
                <Stack gap={4}>
                  <Text fz="sm" c="orange" fw={500}>
                    Let kratší než minuta – jak ho brát?
                  </Text>
                  <SegmentedControl
                    value={kratky}
                    onChange={setKratky}
                    data={[
                      { value: 'start_bez_doby', label: 'Start, doba 0' },
                      { value: 'normalni', label: 'Normální let' },
                    ]}
                  />
                </Stack>
              )}
              {casPristani < casVzletu && (
                <Alert color="red">Přistání je dřív než vzlet.</Alert>
              )}
              <Button
                size="lg"
                loading={zalozeni.isPending}
                disabled={casPristani < casVzletu}
                onClick={() => zalozeni.mutate('dopsat')}
              >
                Zapsat proběhlý let
              </Button>
              <Button variant="subtle" onClick={() => setRezim(null)}>
                Zpět
              </Button>
            </>
          )}
        </Stack>
      )}

      {krok > 0 && krok < 4 && (
        <Group justify="space-between" mt="lg">
          <Button variant="default" onClick={() => setKrok(krok - 1)}>
            Zpět
          </Button>
          {krok !== 1 && (
            <Button disabled={!muzeDal} onClick={() => setKrok(krok + 1)}>
              Dál
            </Button>
          )}
        </Group>
      )}
      {krok === 4 && rezim === null && (
        <Button variant="subtle" mt="md" onClick={() => setKrok(3)}>
          Zpět
        </Button>
      )}
    </Modal>
  )
}
