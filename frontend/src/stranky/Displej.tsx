import { Badge, Box, Card, Center, Grid, Group, Stack, Text, Title } from '@mantine/core'
import { useQuery } from '@tanstack/react-query'
import { useEffect } from 'react'
import { useParams } from 'react-router'

import { type DisplejLet, nactiDisplej } from '../api/displej'
import { ApiChyba } from '../api/klient'
import { bezi, datumCesky, doba, hhmm, hhmmss } from '../cas'
import { KATEGORIE_LETU } from '../nazvy'
import { useServerovyCas } from '../useLety'
import { varovani } from '../varovani'

// Velikosti písma rostou s šířkou obrazovky: čitelné z dálky na TV i na tabletu.
const PISMO = {
  obri: 'clamp(2.2rem, 5vw, 5.5rem)',
  velke: 'clamp(1.6rem, 2.8vw, 3.2rem)',
  stredni: 'clamp(1.1rem, 1.6vw, 1.9rem)',
  male: 'clamp(0.95rem, 1.15vw, 1.35rem)',
}

const pocetLetu = (n: number) => `${n} ${n === 1 ? 'let' : n >= 2 && n <= 4 ? 'lety' : 'letů'}`

const posadka = (l: DisplejLet) =>
  l.posadka
    .map((p) => {
      if (p.funkce === 'clen') return p.jmeno
      return `${p.jmeno} (${p.funkce === 'pic' ? 'PIC' : p.funkce_nazev.toLowerCase()})`
    })
    .join(', ') + (l.pocet_hostu > 0 ? ` + ${l.pocet_hostu} host.` : '')

/** Obrazovka nesmí během provozu usnout (Wake Lock API; kde není, nic se neděje). */
function useBdelaObrazovka() {
  useEffect(() => {
    let zamek: WakeLockSentinel | null = null
    const pozadat = async () => {
      if (!('wakeLock' in navigator)) return
      try {
        zamek = await navigator.wakeLock.request('screen')
      } catch {
        zamek = null
      }
    }
    const priNavratu = () => {
      if (document.visibilityState === 'visible') void pozadat()
    }
    void pozadat()
    document.addEventListener('visibilitychange', priNavratu)
    return () => {
      document.removeEventListener('visibilitychange', priNavratu)
      void zamek?.release()
    }
  }, [])
}

function LetVeVzduchu({ l, ted, soumrak }: { l: DisplejLet; ted: Date; soumrak: string }) {
  const pozor = varovani(l, ted, soumrak)
  return (
    <Card
      withBorder
      padding="md"
      style={pozor ? { borderColor: 'var(--mantine-color-red-6)', borderWidth: 3 } : undefined}
    >
      <Group justify="space-between" align="flex-start" wrap="nowrap">
        <Stack gap={4}>
          <Group gap="sm" align="baseline">
            <Text fw={800} style={{ fontSize: PISMO.velke, lineHeight: 1.1 }}>
              {l.imatrikulace}
            </Text>
            <Text c="dimmed" style={{ fontSize: PISMO.male }}>
              {l.typ}
            </Text>
          </Group>
          <Text style={{ fontSize: PISMO.stredni }}>{posadka(l)}</Text>
          <Text c="dimmed" style={{ fontSize: PISMO.male }}>
            {KATEGORIE_LETU[l.kategorie]} · {l.ucel_nazev.toLowerCase()}
            {l.zpusob_vzletu !== 'vlastni' && ` · ${l.zpusob_nazev.toLowerCase()}`} · vzlet{' '}
            {l.misto_vzletu} {hhmm(l.cas_vzletu)}
            {l.pocet_tg > 0 &&
              ` · T&G ${l.pocet_tg}${l.casy_tg.length ? ` (naposledy ${hhmm(l.casy_tg[l.casy_tg.length - 1])})` : ''}`}
          </Text>
          {l.vlek && (
            <Text c="blue" style={{ fontSize: PISMO.male }}>
              ⇄ {l.vlek}
            </Text>
          )}
          {pozor && (
            <Text c="red" fw={700} style={{ fontSize: PISMO.male }}>
              {pozor}
            </Text>
          )}
        </Stack>
        <Text
          ff="monospace"
          fw={800}
          c={pozor ? 'red' : undefined}
          style={{ fontSize: PISMO.velke, whiteSpace: 'nowrap' }}
        >
          {l.cas_vzletu ? bezi(l.cas_vzletu, ted) : '–'}
        </Text>
      </Group>
    </Card>
  )
}

function Nadpis({ children }: { children: React.ReactNode }) {
  return (
    <Title order={2} style={{ fontSize: PISMO.stredni }} c="dimmed" tt="uppercase">
      {children}
    </Title>
  )
}

/** Velký displej pro věž nebo klubovnu: jen ke čtení, bez přihlášení, tajným odkazem. */
export function Displej() {
  const { klic = '' } = useParams()
  useBdelaObrazovka()
  const dotaz = useQuery({
    queryKey: ['displej', klic],
    queryFn: () => nactiDisplej(klic),
    refetchInterval: 10_000,
    refetchIntervalInBackground: true,
    retry: (pokus, chyba) => !(chyba instanceof ApiChyba && chyba.status === 404) && pokus < 3,
  })
  const d = dotaz.data
  const ted = useServerovyCas(d?.ted)

  if (dotaz.error instanceof ApiChyba && dotaz.error.status === 404) {
    return (
      <Center h="100vh" p="xl">
        <Stack align="center">
          <Title>Odkaz na displej neplatí</Title>
          <Text c="dimmed">Nový odkaz najde admin v administraci: Nastavení provozu → Velký displej.</Text>
        </Stack>
      </Center>
    )
  }
  if (!d) {
    return (
      <Center h="100vh">
        <Text c="dimmed">Načítám…</Text>
      </Center>
    )
  }

  const veVzduchu = d.lety.filter((l) => l.stav === 've_vzduchu')
  const pripravene = d.lety.filter((l) => l.stav === 'pripraven')
  const ukoncene = d.lety.filter((l) => l.stav === 'ukoncen').reverse()
  const s = d.souhrn.celkem

  return (
    <Box p={{ base: 'sm', md: 'lg' }} mih="100vh">
      <Group justify="space-between" align="center" mb="md" wrap="wrap" gap="xs">
        <Stack gap={0}>
          <Text fw={800} style={{ fontSize: PISMO.velke }}>
            LKKL
          </Text>
          <Text c="dimmed" tt="capitalize" style={{ fontSize: PISMO.male }}>
            {datumCesky(d.den)}
          </Text>
        </Stack>
        <Stack gap={0} align="center">
          <Text ff="monospace" fw={800} style={{ fontSize: PISMO.obri, lineHeight: 1 }}>
            {hhmmss(ted)}
          </Text>
          <Text c="dimmed" style={{ fontSize: PISMO.male }}>
            UTC
          </Text>
        </Stack>
        <Stack gap={0} align="flex-end">
          <Text style={{ fontSize: PISMO.stredni }}>Západ slunce {hhmm(d.zapad_slunce)}</Text>
          <Text style={{ fontSize: PISMO.stredni }}>
            Konec soumraku {hhmm(d.konec_soumraku)}
          </Text>
          {dotaz.isError && (
            <Badge color="red" size="lg">
              bez spojení se serverem
            </Badge>
          )}
        </Stack>
      </Group>

      <Grid gap="lg">
        <Grid.Col span={{ base: 12, lg: 8 }}>
          <Stack gap="sm">
            <Nadpis>Ve vzduchu ({veVzduchu.length})</Nadpis>
            {veVzduchu.length === 0 && (
              <Text c="dimmed" style={{ fontSize: PISMO.stredni }}>
                Nikdo nelétá.
              </Text>
            )}
            {veVzduchu.map((l) => (
              <LetVeVzduchu key={l.id} l={l} ted={ted} soumrak={d.konec_soumraku} />
            ))}
          </Stack>
        </Grid.Col>

        <Grid.Col span={{ base: 12, lg: 4 }}>
          <Stack gap="lg">
            {pripravene.length > 0 && (
              <Stack gap={6}>
                <Nadpis>Připravené ({pripravene.length})</Nadpis>
                {pripravene.map((l) => (
                  <Text key={l.id} style={{ fontSize: PISMO.stredni }}>
                    <b>{l.imatrikulace}</b> {posadka(l)}
                  </Text>
                ))}
              </Stack>
            )}

            <Stack gap={6}>
              <Nadpis>Dnes</Nadpis>
              <Group gap="xl">
                {[
                  ['Lety', s.lety],
                  ['Doba', doba(s.minuty)],
                  ['Přistání vč. T&G', s.pristani ?? '–'],
                ].map(([nazev, hodnota]) => (
                  <Stack key={nazev} gap={0}>
                    <Text c="dimmed" style={{ fontSize: PISMO.male }}>
                      {nazev}
                    </Text>
                    <Text fw={800} style={{ fontSize: PISMO.velke }}>
                      {hodnota}
                    </Text>
                  </Stack>
                ))}
              </Group>
              {d.souhrn.podle_letadel.map((r) => (
                <Group key={`${r.imatrikulace}-${r.ucel}`} justify="space-between">
                  <Text style={{ fontSize: PISMO.male }}>
                    <b>{r.imatrikulace}</b> {r.ucel === 'Vlek' ? '(vlek)' : ''}
                  </Text>
                  <Text style={{ fontSize: PISMO.male }}>
                    {pocetLetu(r.lety)} · {r.pristani ?? '–'} přist. · {doba(r.minuty)}
                  </Text>
                </Group>
              ))}
            </Stack>

            {ukoncene.length > 0 && (
              <Stack gap={6}>
                <Nadpis>Naposledy přistáli</Nadpis>
                {ukoncene.slice(0, 8).map((l) => (
                  <Group key={l.id} justify="space-between" wrap="nowrap">
                    <Text style={{ fontSize: PISMO.male }} truncate>
                      <b>{l.imatrikulace}</b> {l.posadka[0]?.jmeno}
                    </Text>
                    <Text ff="monospace" style={{ fontSize: PISMO.male, whiteSpace: 'nowrap' }}>
                      {hhmm(l.cas_vzletu)}–{hhmm(l.cas_pristani)} · {doba(l.doba_uctovana_min)}
                      {l.pocet_pristani > 1 && ` · ${l.pocet_pristani} přist.`}
                    </Text>
                  </Group>
                ))}
              </Stack>
            )}
          </Stack>
        </Grid.Col>
      </Grid>
    </Box>
  )
}
