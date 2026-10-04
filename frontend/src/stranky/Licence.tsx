import {
  Alert,
  Anchor,
  Badge,
  Button,
  Card,
  Checkbox,
  Container,
  Group,
  Loader,
  Modal,
  Select,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useSearchParams } from 'react-router'

import {
  type KvalifikaceData,
  type Licence as LicenceData,
  type LicenceStav,
  nactiLicence,
  smazatLicenci,
  ulozitLicenci,
  ulozitMedicalTridy,
} from '../api/licence'

const datum = (iso: string | null) =>
  iso ? new Date(`${iso}T12:00:00Z`).toLocaleDateString('cs-CZ', { timeZone: 'UTC' }) : null

/** Uložení vrací nový stav licencí; obnoví se i přehledy, které z nich počítají. */
function useUlozeni<T>(
  osoba: number | null,
  fn: (data: T) => Promise<LicenceStav>,
  zprava: string,
  hotovo: () => void,
) {
  const klient = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: (stav) => {
      klient.setQueryData(['licence', osoba], stav)
      void klient.invalidateQueries({ queryKey: ['rozletanost'] })
      void klient.invalidateQueries({ queryKey: ['sprava'] })
      notifications.show({ message: zprava, color: 'green' })
      hotovo()
    },
    onError: (e) => notifications.show({ message: e.message, color: 'red' }),
  })
}

function LicenceDialog({
  stav,
  osoba,
  licence,
  onZavrit,
}: {
  stav: LicenceStav
  osoba: number | null
  licence: LicenceData | null
  onZavrit: () => void
}) {
  const [typ, setTyp] = useState<string | null>(licence?.typ ?? null)
  const [cislo, setCislo] = useState(licence?.cislo ?? '')
  const [poznamka, setPoznamka] = useState(licence?.poznamka ?? '')
  const [kvalifikace, setKvalifikace] = useState<KvalifikaceData[]>(licence?.kvalifikace ?? [])
  const ulozeni = useUlozeni(
    osoba,
    (data: Omit<LicenceData, 'id'> & { id?: number }) => ulozitLicenci(data, osoba),
    'Licence uložena.',
    onZavrit,
  )
  const smazani = useUlozeni(osoba, (id: number) => smazatLicenci(id, osoba), 'Licence smazána.', onZavrit)
  const moznosti = typ ? stav.kvalifikace[typ] : []
  const zapnuta = (druh: string) => kvalifikace.find((k) => k.druh === druh)

  const prepnout = (druh: string, ano: boolean) =>
    setKvalifikace(
      ano ? [...kvalifikace, { druh, platnost_do: null }] : kvalifikace.filter((k) => k.druh !== druh),
    )
  const nastavDatum = (druh: string, platnost_do: string) =>
    setKvalifikace(kvalifikace.map((k) => (k.druh === druh ? { ...k, platnost_do: platnost_do || null } : k)))

  const nadpisKvalifikaci =
    typ === 'spl'
      ? 'Způsoby vzletu a TMG'
      : typ === 'jazyk'
        ? 'Úroveň (jen jedna)'
        : typ === 'ull' || typ === 'radio'
          ? 'Druh a platnost'
          : 'Třídy'

  return (
    <Modal opened onClose={onZavrit} title={licence ? 'Upravit licenci' : 'Přidat licenci'} centered>
      <Stack>
        <Select
          label="Typ licence"
          data={stav.typy.map((t) => ({ value: t.hodnota, label: t.nazev }))}
          value={typ}
          onChange={(v) => {
            setTyp(v)
            setKvalifikace([])
          }}
          allowDeselect={false}
        />
        <TextInput label="Číslo průkazu (nepovinné)" value={cislo} onChange={(e) => setCislo(e.currentTarget.value)} />
        {moznosti.length > 0 && (
          <Stack gap="xs">
            <Text fz="sm" fw={500}>
              {nadpisKvalifikaci}
            </Text>
            {moznosti.map((m) => {
              const k = zapnuta(m.hodnota)
              return (
                <Group key={m.hodnota} justify="space-between" wrap="nowrap">
                  <Checkbox
                    label={m.nazev}
                    checked={!!k}
                    onChange={(e) => prepnout(m.hodnota, e.currentTarget.checked)}
                  />
                  {k && (
                    <TextInput
                      type="date"
                      size="xs"
                      aria-label={`${m.nazev} platí do`}
                      value={k.platnost_do ?? ''}
                      onChange={(e) => nastavDatum(m.hodnota, e.currentTarget.value)}
                    />
                  )}
                </Group>
              )
            })}
            <Text fz="xs" c="dimmed">
              Datum vyplňte u PPL(A) (konec platnosti SEP/TMG), u ULL a radiofonního průkazu. U LAPL(A) a
              SPL se platnost hlídá náletem. Angličtina ICAO je jen informace (úroveň 6 platí trvale).
            </Text>
          </Stack>
        )}
        <TextInput label="Poznámka (nepovinné)" value={poznamka} onChange={(e) => setPoznamka(e.currentTarget.value)} />
        <Group justify="space-between">
          {licence ? (
            <Button variant="subtle" color="red" loading={smazani.isPending} onClick={() => smazani.mutate(licence.id)}>
              Smazat
            </Button>
          ) : (
            <span />
          )}
          <Button
            disabled={!typ}
            loading={ulozeni.isPending}
            onClick={() => ulozeni.mutate({ id: licence?.id, typ: typ!, cislo, poznamka, kvalifikace })}
          >
            Uložit
          </Button>
        </Group>
      </Stack>
    </Modal>
  )
}

/** Medical jako jedno osvědčení: pro každou třídu vlastní datum platnosti (nebo nic). */
function MedicalDialog({ stav, osoba, onZavrit }: { stav: LicenceStav; osoba: number | null; onZavrit: () => void }) {
  const [tridy, setTridy] = useState<Record<string, string>>(() =>
    Object.fromEntries(stav.tridy.map((t) => [t.hodnota, stav.medicaly.find((m) => m.trida === t.hodnota)?.platnost_do ?? ''])),
  )
  const ulozeni = useUlozeni(
    osoba,
    (data: Record<string, string>) =>
      ulozitMedicalTridy(Object.fromEntries(Object.entries(data).map(([t, d]) => [t, d || null])), osoba),
    'Medical uložen.',
    onZavrit,
  )
  return (
    <Modal opened onClose={onZavrit} title="Medical" centered>
      <Stack>
        <Text fz="sm" c="dimmed">
          Vyplňte platnost u tříd, které osvědčení obsahuje (např. třída 2 i LAPL mají jiné datum). Prázdné
          pole = třídu nemáte.
        </Text>
        {stav.tridy.map((t) => (
          <TextInput
            key={t.hodnota}
            type="date"
            label={`${t.nazev} – platí do`}
            value={tridy[t.hodnota]}
            onChange={(e) => setTridy({ ...tridy, [t.hodnota]: e.currentTarget.value })}
          />
        ))}
        <Button loading={ulozeni.isPending} onClick={() => ulozeni.mutate(tridy)}>
          Uložit
        </Button>
      </Stack>
    </Modal>
  )
}

/** Licence a medical: pilot spravuje své, správce a admin kohokoli (?osoba=ID). */
export function Licence() {
  const [parametry] = useSearchParams()
  const osoba = parametry.get('osoba') ? Number(parametry.get('osoba')) : null
  const stav = useQuery({ queryKey: ['licence', osoba], queryFn: () => nactiLicence(osoba) })
  const [licence, setLicence] = useState<LicenceData | null | undefined>(undefined)
  const [medical, setMedical] = useState(false)
  const s = stav.data
  const nazev = (seznam: { hodnota: string; nazev: string }[], h: string) =>
    seznam.find((v) => v.hodnota === h)?.nazev ?? h

  return (
    <Container size="sm" pb="xl">
      <Stack gap="md">
        <div>
          <Title order={2}>Licence a medical{osoba && s ? ` – ${s.jmeno}` : ''}</Title>
          <Text c="dimmed" fz="sm">
            Podle těchto údajů aplikace hlídá platnost a rozlétanost (Můj nálet) a varuje při zakládání
            letu.
          </Text>
          {osoba && (
            <Anchor component={Link} to="/sprava" fz="sm">
              ← Piloti a letadla
            </Anchor>
          )}
        </div>
        {stav.isPending && <Loader />}
        {stav.isError && <Alert color="red">{stav.error.message}</Alert>}
        {s && (
          <>
            <Group justify="space-between">
              <Title order={4}>Licence</Title>
              <Button size="xs" variant="light" onClick={() => setLicence(null)}>
                + Přidat licenci
              </Button>
            </Group>
            {s.licence.length === 0 && <Text c="dimmed">Zatím žádná licence.</Text>}
            {s.licence.map((l) => (
              <Card key={l.id} withBorder padding="sm" onClick={() => setLicence(l)} style={{ cursor: 'pointer' }}>
                <Group justify="space-between">
                  <Text fw={700}>{nazev(s.typy, l.typ)}</Text>
                  {l.cislo && (
                    <Text fz="sm" c="dimmed">
                      {l.cislo}
                    </Text>
                  )}
                </Group>
                <Group gap={6} mt={4}>
                  {l.kvalifikace.map((k) => (
                    <Badge key={k.druh} variant="light">
                      {nazev(s.kvalifikace[l.typ], k.druh)}
                      {k.platnost_do && ` do ${datum(k.platnost_do)}`}
                    </Badge>
                  ))}
                </Group>
                {l.poznamka && (
                  <Text fz="sm" c="dimmed" mt={4}>
                    {l.poznamka}
                  </Text>
                )}
              </Card>
            ))}

            <Group justify="space-between" mt="md">
              <Title order={4}>Medical</Title>
              <Button size="xs" variant="light" onClick={() => setMedical(true)}>
                {s.medicaly.length ? 'Upravit medical' : '+ Zadat medical'}
              </Button>
            </Group>
            {s.medicaly.length === 0 ? (
              <Text c="dimmed">Zatím nezadaný.</Text>
            ) : (
              <Card withBorder padding="sm" onClick={() => setMedical(true)} style={{ cursor: 'pointer' }}>
                <Group gap={6}>
                  {s.medicaly.map((m) => (
                    <Badge key={m.id} variant="light">
                      {nazev(s.tridy, m.trida)} do {datum(m.platnost_do)}
                    </Badge>
                  ))}
                </Group>
              </Card>
            )}
          </>
        )}
      </Stack>
      {s && licence !== undefined && (
        <LicenceDialog stav={s} osoba={osoba} licence={licence} onZavrit={() => setLicence(undefined)} />
      )}
      {s && medical && <MedicalDialog stav={s} osoba={osoba} onZavrit={() => setMedical(false)} />}
    </Container>
  )
}
