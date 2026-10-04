import {
  Alert,
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

import {
  type KvalifikaceData,
  type Licence as LicenceData,
  type LicenceStav,
  type Medical,
  nactiLicence,
  smazatLicenci,
  smazatMedical,
  ulozitLicenci,
  ulozitMedical,
} from '../api/licence'

const KLIC = ['licence']

const datum = (iso: string | null) =>
  iso ? new Date(`${iso}T12:00:00Z`).toLocaleDateString('cs-CZ', { timeZone: 'UTC' }) : null

function useUlozeni<T>(fn: (data: T) => Promise<LicenceStav>, zprava: string, hotovo: () => void) {
  const klient = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: (stav) => {
      klient.setQueryData(KLIC, stav)
      void klient.invalidateQueries({ queryKey: ['rozletanost'] })
      notifications.show({ message: zprava, color: 'green' })
      hotovo()
    },
    onError: (e) => notifications.show({ message: e.message, color: 'red' }),
  })
}

function LicenceDialog({
  stav,
  licence,
  onZavrit,
}: {
  stav: LicenceStav
  licence: LicenceData | null
  onZavrit: () => void
}) {
  const [typ, setTyp] = useState<string | null>(licence?.typ ?? null)
  const [cislo, setCislo] = useState(licence?.cislo ?? '')
  const [poznamka, setPoznamka] = useState(licence?.poznamka ?? '')
  const [kvalifikace, setKvalifikace] = useState<KvalifikaceData[]>(licence?.kvalifikace ?? [])
  const ulozeni = useUlozeni(ulozitLicenci, 'Licence uložena.', onZavrit)
  const smazani = useUlozeni(smazatLicenci, 'Licence smazána.', onZavrit)
  const moznosti = typ ? stav.kvalifikace[typ] : []
  const zapnuta = (druh: string) => kvalifikace.find((k) => k.druh === druh)

  const prepnout = (druh: string, ano: boolean) =>
    setKvalifikace(
      ano ? [...kvalifikace, { druh, platnost_do: null }] : kvalifikace.filter((k) => k.druh !== druh),
    )
  const nastavDatum = (druh: string, platnost_do: string) =>
    setKvalifikace(kvalifikace.map((k) => (k.druh === druh ? { ...k, platnost_do: platnost_do || null } : k)))

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
              {typ === 'spl' ? 'Způsoby vzletu a TMG' : typ === 'ull' ? 'Platnost průkazu' : 'Třídy'}
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
              Datum vyplňte u PPL(A) (konec platnosti SEP/TMG) a u ULL (platnost průkazu). U LAPL(A) a
              SPL se platnost nehlídá datem, ale náletem.
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

function MedicalDialog({
  stav,
  medical,
  onZavrit,
}: {
  stav: LicenceStav
  medical: Medical | null
  onZavrit: () => void
}) {
  const [trida, setTrida] = useState<string | null>(medical?.trida ?? '2')
  const [platnost, setPlatnost] = useState(medical?.platnost_do ?? '')
  const ulozeni = useUlozeni(ulozitMedical, 'Medical uložen.', onZavrit)
  const smazani = useUlozeni(smazatMedical, 'Medical smazán.', onZavrit)
  return (
    <Modal opened onClose={onZavrit} title={medical ? 'Upravit medical' : 'Přidat medical'} centered>
      <Stack>
        <Select
          label="Třída"
          data={stav.tridy.map((t) => ({ value: t.hodnota, label: t.nazev }))}
          value={trida}
          onChange={setTrida}
          allowDeselect={false}
        />
        <TextInput type="date" label="Platí do" value={platnost} onChange={(e) => setPlatnost(e.currentTarget.value)} />
        <Group justify="space-between">
          {medical ? (
            <Button variant="subtle" color="red" loading={smazani.isPending} onClick={() => smazani.mutate(medical.id)}>
              Smazat
            </Button>
          ) : (
            <span />
          )}
          <Button
            disabled={!trida || !platnost}
            loading={ulozeni.isPending}
            onClick={() => ulozeni.mutate({ id: medical?.id, trida: trida!, platnost_do: platnost })}
          >
            Uložit
          </Button>
        </Group>
      </Stack>
    </Modal>
  )
}

/** Moje licence a medical – pilot je spravuje sám (admin všechny v administraci). */
export function Licence() {
  const stav = useQuery({ queryKey: KLIC, queryFn: nactiLicence })
  const [licence, setLicence] = useState<LicenceData | null | undefined>(undefined)
  const [medical, setMedical] = useState<Medical | null | undefined>(undefined)
  const s = stav.data
  const nazev = (seznam: { hodnota: string; nazev: string }[], h: string) =>
    seznam.find((v) => v.hodnota === h)?.nazev ?? h

  return (
    <Container size="sm" pb="xl">
      <Stack gap="md">
        <div>
          <Title order={2}>Licence a medical</Title>
          <Text c="dimmed" fz="sm">
            Podle těchto údajů aplikace hlídá platnost a rozlétanost (Můj nálet) a varuje při zakládání
            letu.
          </Text>
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
              <Button size="xs" variant="light" onClick={() => setMedical(null)}>
                + Přidat medical
              </Button>
            </Group>
            {s.medicaly.length === 0 && <Text c="dimmed">Zatím žádný medical.</Text>}
            {s.medicaly.map((m) => (
              <Card key={m.id} withBorder padding="sm" onClick={() => setMedical(m)} style={{ cursor: 'pointer' }}>
                <Group justify="space-between">
                  <Text fw={700}>{nazev(s.tridy, m.trida)}</Text>
                  <Text fz="sm">platí do {datum(m.platnost_do)}</Text>
                </Group>
              </Card>
            ))}
          </>
        )}
      </Stack>
      {s && licence !== undefined && (
        <LicenceDialog stav={s} licence={licence} onZavrit={() => setLicence(undefined)} />
      )}
      {s && medical !== undefined && (
        <MedicalDialog stav={s} medical={medical} onZavrit={() => setMedical(undefined)} />
      )}
    </Container>
  )
}
