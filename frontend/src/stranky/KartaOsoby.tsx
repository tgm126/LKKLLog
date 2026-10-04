import {
  Alert,
  Anchor,
  Button,
  Checkbox,
  CloseButton,
  Container,
  Grid,
  Group,
  Loader,
  MultiSelect,
  Paper,
  Select,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { type ReactNode, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'

import {
  type Karta,
  type KartaIn,
  nactiKartu,
  nactiTelefon,
  nactiVolbyOsob,
  type PrukazData,
  ulozitKartu,
  type VolbaDruhu,
  type Volby,
  type VycvikData,
} from '../api/osoby'
import { SeznamKontrol } from '../komponenty/Rozletanost'
import { KATEGORIE_LETU } from '../nazvy'
import { useJa } from '../useJa'

const PRAZDNA: KartaIn = {
  jmeno: '',
  prijmeni: '',
  email: null,
  aktivni: true,
  externi: false,
  testovaci: false,
  role: { casomeric: false, ucetni: false, spravce: false, admin: false },
  prukazy: [],
  provozni: [],
  preskoleni: [],
  vycviky: [],
}

/** Nadpis oddílu karty – jedna menší velikost, šedě. */
function Oddil({ nazev, children, akce }: { nazev: string; children: ReactNode; akce?: ReactNode }) {
  return (
    <Stack gap={6}>
      <Group justify="space-between" wrap="nowrap" mih={22}>
        <Text fz="xs" fw={600} c="dimmed">
          {nazev}
        </Text>
        {akce}
      </Group>
      {children}
    </Stack>
  )
}

/** Datum platnosti: malé pole vedle zaškrtnuté kvalifikace. */
function Datum({ hodnota, onZmena, popis }: { hodnota: string | null; onZmena: (d: string | null) => void; popis: string }) {
  return (
    <TextInput
      type="date"
      size="xs"
      w={132}
      aria-label={popis}
      value={hodnota ?? ''}
      onChange={(e) => onZmena(e.currentTarget.value || null)}
    />
  )
}

/** Řádek průkazu: název, číslo a zaškrtávátka kvalifikací (s datem, kde má platnost). */
function RadekPrukazu({
  druh,
  data,
  onZmena,
  cislo = true,
  odebrat = true,
}: {
  druh: VolbaDruhu
  data: PrukazData | undefined
  onZmena: (p: PrukazData | undefined) => void
  cislo?: boolean
  odebrat?: boolean
}) {
  const p = data ?? { druh_id: druh.id, cislo: '', poznamka: '', kvalifikace: [] }
  const kv = (id: number) => p.kvalifikace.find((k) => k.kvalifikace_id === id)
  const zmenit = (zmena: Partial<PrukazData>) => {
    const novy = { ...p, ...zmena }
    // Doklad bez kvalifikací a bez čísla (medical, radio) se neukládá.
    onZmena(!odebrat && novy.kvalifikace.length === 0 && !novy.cislo ? undefined : novy)
  }
  const prepnout = (id: number, ano: boolean) =>
    zmenit({
      kvalifikace: ano
        ? [...p.kvalifikace, { kvalifikace_id: id, platnost_do: null }]
        : p.kvalifikace.filter((k) => k.kvalifikace_id !== id),
    })
  const datum = (id: number, platnost_do: string | null) =>
    zmenit({ kvalifikace: p.kvalifikace.map((k) => (k.kvalifikace_id === id ? { ...k, platnost_do } : k)) })

  return (
    <Paper withBorder px="sm" py={6} radius="sm">
      <Group justify="space-between" wrap="nowrap" gap="xs">
        <Text fz="sm" fw={600}>
          {druh.nazev}
        </Text>
        <Group gap={6} wrap="nowrap">
          {cislo && (
            <TextInput
              size="xs"
              w={150}
              placeholder="číslo průkazu"
              aria-label={`${druh.nazev} číslo`}
              value={p.cislo}
              onChange={(e) => zmenit({ cislo: e.currentTarget.value })}
            />
          )}
          {odebrat && <CloseButton size="sm" aria-label={`Odebrat ${druh.nazev}`} onClick={() => onZmena(undefined)} />}
        </Group>
      </Group>
      <Group gap="md" mt={6} style={{ rowGap: 6 }}>
        {druh.kvalifikace
          .filter((k) => k.aktivni || kv(k.id))
          .map((k) => {
            const zvolena = kv(k.id)
            return (
              <Group key={k.id} gap={6} wrap="nowrap">
                <Checkbox
                  size="sm"
                  label={k.nazev}
                  checked={!!zvolena}
                  onChange={(e) => prepnout(k.id, e.currentTarget.checked)}
                />
                {zvolena && k.ma_platnost && (
                  <Datum hodnota={zvolena.platnost_do} onZmena={(d) => datum(k.id, d)} popis={`${k.nazev} platí do`} />
                )}
              </Group>
            )
          })}
      </Group>
    </Paper>
  )
}

/** Skupina průkazů (pilotní, instruktor…): řádky a výběr pro přidání dalšího druhu. */
function SkupinaPrukazu({
  nazev,
  skupiny,
  volby,
  data,
  onZmena,
}: {
  nazev: string
  skupiny: string[]
  volby: Volby
  data: KartaIn
  onZmena: (prukazy: PrukazData[]) => void
}) {
  const druhy = volby.druhy.filter((d) => skupiny.includes(d.skupina))
  const ma = data.prukazy.filter((p) => druhy.some((d) => d.id === p.druh_id))
  const pridat = druhy.filter((d) => d.aktivni && !ma.some((p) => p.druh_id === d.id))
  const nahradit = (druh_id: number, p: PrukazData | undefined) =>
    onZmena(
      p
        ? data.prukazy.some((x) => x.druh_id === druh_id)
          ? data.prukazy.map((x) => (x.druh_id === druh_id ? p : x))
          : [...data.prukazy, p]
        : data.prukazy.filter((x) => x.druh_id !== druh_id),
    )
  return (
    <Oddil
      nazev={nazev}
      akce={
        pridat.length > 0 && (
          <Select
            size="xs"
            w={190}
            placeholder="+ přidat"
            data={pridat.map((d) => ({ value: String(d.id), label: d.nazev }))}
            value={null}
            onChange={(v) => v && nahradit(Number(v), { druh_id: Number(v), cislo: '', poznamka: '', kvalifikace: [] })}
          />
        )
      }
    >
      {ma.length === 0 && (
        <Text fz="sm" c="dimmed">
          žádný
        </Text>
      )}
      {ma.map((p) => {
        const druh = druhy.find((d) => d.id === p.druh_id)!
        return <RadekPrukazu key={p.druh_id} druh={druh} data={p} onZmena={(n) => nahradit(p.druh_id, n)} />
      })}
    </Oddil>
  )
}

function Vycviky({ volby, vycviky, onZmena }: { volby: Volby; vycviky: VycvikData[]; onZmena: (v: VycvikData[]) => void }) {
  const piloti = volby.druhy.filter((d) => d.skupina === 'pilotni' && d.aktivni)
  const zmenit = (i: number, zmena: Partial<VycvikData>) => onZmena(vycviky.map((v, j) => (j === i ? { ...v, ...zmena } : v)))
  return (
    <Oddil
      nazev="Výcvik (žák)"
      akce={
        <Button
          size="compact-xs"
          variant="subtle"
          onClick={() =>
            onZmena([...vycviky, { druh_id: piloti[0].id, zahajen: null, solo_povoleno: null, ukoncen: null, poznamka: '' }])
          }
        >
          + zahájit výcvik
        </Button>
      }
    >
      {vycviky.length === 0 && (
        <Text fz="sm" c="dimmed">
          není ve výcviku
        </Text>
      )}
      {vycviky.map((v, i) => (
        <Paper key={i} withBorder px="sm" py={6} radius="sm">
          <Group gap="xs" wrap="wrap" align="flex-end">
            <Select
              size="xs"
              w={150}
              label="na průkaz"
              data={piloti.map((d) => ({ value: String(d.id), label: d.nazev }))}
              value={String(v.druh_id)}
              onChange={(d) => d && zmenit(i, { druh_id: Number(d) })}
              allowDeselect={false}
            />
            {(['zahajen', 'solo_povoleno', 'ukoncen'] as const).map((pole) => (
              <TextInput
                key={pole}
                type="date"
                size="xs"
                w={132}
                label={{ zahajen: 'zahájen', solo_povoleno: 'sólo povoleno', ukoncen: 'ukončen' }[pole]}
                value={v[pole] ?? ''}
                onChange={(e) => zmenit(i, { [pole]: e.currentTarget.value || null })}
              />
            ))}
            <CloseButton size="sm" aria-label="Odebrat výcvik" onClick={() => onZmena(vycviky.filter((_, j) => j !== i))} />
          </Group>
        </Paper>
      ))}
    </Oddil>
  )
}

function Formular({ id, karta, volby }: { id: number | null; karta: Karta | null; volby: Volby }) {
  const { data: ja } = useJa()
  const admin = !!ja?.role?.admin
  const klient = useQueryClient()
  const navigate = useNavigate()
  const [data, setData] = useState<KartaIn>(() => (karta ? { ...karta } : PRAZDNA))
  const [telefon, setTelefon] = useState<string | null>(null) // null = nenačtený, nemění se
  const nastav = (zmena: Partial<KartaIn>) => setData({ ...data, ...zmena })

  const ukazTelefon = useMutation({
    mutationFn: () => nactiTelefon(id!),
    onSuccess: (t) => setTelefon(t.telefon),
  })
  const ulozeni = useMutation({
    mutationFn: () => ulozitKartu(id, { ...data, telefon: telefon ?? (id ? undefined : null) }),
    onSuccess: (k) => {
      klient.setQueryData(['sprava', 'osoba', k.id], k)
      void klient.invalidateQueries({ queryKey: ['sprava', 'osoby'] })
      void klient.invalidateQueries({ queryKey: ['ciselniky'] }) // nabídky v průvodci
      notifications.show({ message: 'Uloženo.', color: 'green' })
      if (!id) navigate(`/osoby/${k.id}`, { replace: true })
    },
    onError: (e) => notifications.show({ message: e.message, color: 'red' }),
  })

  const doklady = (skupina: string) => volby.druhy.filter((d) => d.skupina === skupina)
  const typyPodleKategorie = Object.entries(
    volby.typy
      .filter((t) => t.aktivni || data.preskoleni.includes(t.id))
      .reduce<Record<string, { value: string; label: string }[]>>((g, t) => {
        ;(g[KATEGORIE_LETU[t.kategorie] ?? t.kategorie] ??= []).push({ value: String(t.id), label: t.nazev })
        return g
      }, {}),
  ).map(([group, items]) => ({ group, items }))

  const ulozit = (
    <Button size="compact-sm" loading={ulozeni.isPending} onClick={() => ulozeni.mutate()}>
      Uložit
    </Button>
  )

  return (
    <Stack gap="md">
      <Group justify="space-between" wrap="nowrap">
        <div>
          <Anchor component={Link} to="/osoby" fz="xs">
            ← Osoby
          </Anchor>
          <Title order={3}>{id ? `${data.prijmeni} ${data.jmeno}` : 'Nová osoba'}</Title>
        </div>
        {ulozit}
      </Group>
      <Grid gap="lg">
        <Grid.Col span={{ base: 12, md: 6 }}>
          <Stack gap="md">
            <Oddil nazev="Údaje">
              <Group grow gap="xs">
                <TextInput size="sm" label="Jméno" value={data.jmeno} onChange={(e) => nastav({ jmeno: e.currentTarget.value })} />
                <TextInput size="sm" label="Příjmení" value={data.prijmeni} onChange={(e) => nastav({ prijmeni: e.currentTarget.value })} />
              </Group>
              <Group grow gap="xs" align="flex-end">
                <TextInput
                  size="sm"
                  label="E-mail"
                  value={data.email ?? ''}
                  onChange={(e) => nastav({ email: e.currentTarget.value || null })}
                />
                {telefon !== null || !id || !karta?.ma_telefon ? (
                  <TextInput size="sm" label="Mobil" value={telefon ?? ''} onChange={(e) => setTelefon(e.currentTarget.value)} />
                ) : (
                  <Button size="sm" variant="default" loading={ukazTelefon.isPending} onClick={() => ukazTelefon.mutate()}>
                    Zobrazit mobil
                  </Button>
                )}
              </Group>
              <Group gap="md">
                <Checkbox size="sm" label="Aktivní" checked={data.aktivni} onChange={(e) => nastav({ aktivni: e.currentTarget.checked })} />
                <Checkbox size="sm" label="Externí" checked={data.externi} onChange={(e) => nastav({ externi: e.currentTarget.checked })} />
                <Checkbox size="sm" label="Testovací" checked={data.testovaci} onChange={(e) => nastav({ testovaci: e.currentTarget.checked })} />
              </Group>
            </Oddil>
            <Oddil nazev={admin ? 'Role v aplikaci' : 'Role v aplikaci (mění admin)'}>
              <Group gap="md">
                {(
                  [
                    ['casomeric', 'časoměřič / věž'],
                    ['ucetni', 'účetní'],
                    ['spravce', 'správce licencí a letadel'],
                    ['admin', 'admin'],
                  ] as const
                ).map(([klic, nazev]) => (
                  <Checkbox
                    key={klic}
                    size="sm"
                    label={nazev}
                    disabled={!admin}
                    checked={data.role[klic]}
                    onChange={(e) => nastav({ role: { ...data.role, [klic]: e.currentTarget.checked } })}
                  />
                ))}
              </Group>
            </Oddil>
            <SkupinaPrukazu
              nazev="Pilotní průkazy a kvalifikace"
              skupiny={['pilotni']}
              volby={volby}
              data={data}
              onZmena={(prukazy) => nastav({ prukazy })}
            />
            <SkupinaPrukazu
              nazev="Instruktor a examinátor"
              skupiny={['instruktor', 'examinator']}
              volby={volby}
              data={data}
              onZmena={(prukazy) => nastav({ prukazy })}
            />
          </Stack>
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 6 }}>
          <Stack gap="md">
            <Oddil nazev="Doklady">
              {['medical', 'radio', 'jazyk'].flatMap(doklady).map((druh) => (
                <RadekPrukazu
                  key={druh.id}
                  druh={druh}
                  cislo={druh.skupina === 'radio'}
                  odebrat={false}
                  data={data.prukazy.find((p) => p.druh_id === druh.id)}
                  onZmena={(p) =>
                    nastav({
                      prukazy: p
                        ? data.prukazy.some((x) => x.druh_id === druh.id)
                          ? data.prukazy.map((x) => (x.druh_id === druh.id ? p : x))
                          : [...data.prukazy, p]
                        : data.prukazy.filter((x) => x.druh_id !== druh.id),
                    })
                  }
                />
              ))}
            </Oddil>
            <Oddil nazev="Přeškolen na typy (platí pro všechna letadla typu)">
              <MultiSelect
                size="sm"
                searchable
                placeholder={data.preskoleni.length ? undefined : 'vyberte typy'}
                data={typyPodleKategorie}
                value={data.preskoleni.map(String)}
                onChange={(v) => nastav({ preskoleni: v.map(Number) })}
              />
            </Oddil>
            <Oddil nazev="Provozní oprávnění">
              <Group gap="md">
                {volby.provozni
                  .filter((o) => o.aktivni || data.provozni.includes(o.id))
                  .map((o) => (
                    <Checkbox
                      key={o.id}
                      size="sm"
                      label={o.nazev}
                      checked={data.provozni.includes(o.id)}
                      onChange={(e) =>
                        nastav({
                          provozni: e.currentTarget.checked
                            ? [...data.provozni, o.id]
                            : data.provozni.filter((x) => x !== o.id),
                        })
                      }
                    />
                  ))}
              </Group>
            </Oddil>
            <Vycviky volby={volby} vycviky={data.vycviky} onZmena={(vycviky) => nastav({ vycviky })} />
            {karta && karta.kontroly.length > 0 && (
              <Oddil nazev="Stav dokladů a rozlétanosti (podle uložených údajů)">
                <SeznamKontrol kontroly={karta.kontroly} />
              </Oddil>
            )}
          </Stack>
        </Grid.Col>
      </Grid>
      <Group justify="flex-end">{ulozit}</Group>
    </Stack>
  )
}

/** Karta osoby: všechno o osobě na jednom místě, hodnoty z číselníků. */
export function KartaOsoby() {
  const { id: parametr } = useParams()
  const id = parametr && parametr !== 'nova' ? Number(parametr) : null
  const volby = useQuery({ queryKey: ['sprava', 'volby-osob'], queryFn: nactiVolbyOsob })
  const karta = useQuery({ queryKey: ['sprava', 'osoba', id], queryFn: () => nactiKartu(id!), enabled: id !== null })
  const chyba = volby.error ?? karta.error
  return (
    <Container size="lg" pb="xl">
      {chyba && <Alert color="red">{chyba.message}</Alert>}
      {(volby.isPending || (id !== null && karta.isPending)) && !chyba && <Loader size="sm" />}
      {volby.data && (id === null || karta.data) && (
        <Formular key={id ?? 'nova'} id={id} karta={karta.data ?? null} volby={volby.data} />
      )}
    </Container>
  )
}
