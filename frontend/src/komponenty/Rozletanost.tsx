import { Alert, Box, Group, Loader, Paper, Stack, Text, Title } from '@mantine/core'
import { useQuery } from '@tanstack/react-query'

import { type Kontrola, kontrolaPosadky, type KontrolaPosadky, nactiRozletanost } from '../api/licence'

const BARVA: Record<Kontrola['stav'], string> = {
  ok: 'green',
  pozor: 'orange',
  chyba: 'red',
  info: 'gray',
}
const ZNAK: Record<Kontrola['stav'], string> = { ok: '✓', pozor: '!', chyba: '✗', info: 'i' }

/** Podrobnosti na jeden řádek; za uvozením s dvojtečkou bez oddělovače. */
const spojit = (p: string[]) => p.reduce((s, x, i) => (i === 0 ? x : s + (s.endsWith(':') ? ' ' : ' · ') + x), '')

/** Seznam kontrol licencí, medicalu a rozlétanosti: hustý seznam řádků s barevným stavem. */
export function SeznamKontrol({ kontroly }: { kontroly: Kontrola[] }) {
  return (
    <Paper withBorder radius="sm">
      {kontroly.map((k, i) => (
        <Box key={i} px="sm" py={5} style={i ? { borderTop: '1px solid var(--mantine-color-default-border)' } : undefined}>
          <Group justify="space-between" wrap="nowrap" align="flex-start" gap="sm">
            <Text fz="sm" fw={500}>
              <Text span c={BARVA[k.stav]} fw={700}>
                {ZNAK[k.stav]}
              </Text>{' '}
              {k.nazev.startsWith(k.oblast) ? k.nazev : `${k.oblast} · ${k.nazev}`}
            </Text>
            <Text fz="sm" ta="right" c={k.stav === 'ok' || k.stav === 'info' ? 'dimmed' : BARVA[k.stav]}>
              {k.text}
            </Text>
          </Group>
          {k.podrobnosti.length > 0 && (
            <Text fz="xs" c="dimmed">
              {spojit(k.podrobnosti)}
            </Text>
          )}
        </Box>
      ))}
    </Paper>
  )
}

/** Přehled licencí, medicalu a rozlétanosti pilota (Můj nálet). */
export function Rozletanost() {
  const dotaz = useQuery({ queryKey: ['rozletanost'], queryFn: nactiRozletanost })
  const d = dotaz.data
  if (dotaz.isPending) return <Loader size="sm" />
  if (!d?.zobrazit) {
    return (
      <Group justify="space-between">
        <Text fz="sm" c="dimmed">
          Průkazy a medical zadává admin na kartě osoby; hlídání rozlétanosti zapne admin.
        </Text>
      </Group>
    )
  }
  return (
    <Stack gap="xs">
      <Group justify="space-between">
        <Title order={4}>Licence a rozlétanost</Title>
        <Text fz="xs" c="dimmed">
          Údaje zadává admin
        </Text>
      </Group>
      {(!d.moduly.zpusobilost || !d.moduly.rozletanost) && (
        <Alert color="gray" p="xs">
          V Nastavení provozu je vypnuté hlídání{' '}
          {[!d.moduly.zpusobilost && 'způsobilosti', !d.moduly.rozletanost && 'rozlétanosti']
            .filter(Boolean)
            .join(' a ')}{' '}
          – tyto kontroly teď vidí jen admin.
        </Alert>
      )}
      <SeznamKontrol kontroly={d.kontroly} />
      <Text fz="xs" c="dimmed">
        Počítá se jen z letů zapsaných v LKKL Log – lety jinde aplikace nezná. Je to pomůcka, za
        rozlétanost odpovídá pilot.
      </Text>
    </Stack>
  )
}

/** Varování k posádce před vzletem (licence, medical, rozlétanost). Nic neblokuje. */
export function VarovaniPosadky({ data }: { data: KontrolaPosadky | null }) {
  const dotaz = useQuery({
    queryKey: ['kontrola-posadky', data],
    queryFn: () => kontrolaPosadky(data!),
    enabled: data !== null,
    staleTime: 30_000,
  })
  const varovani = dotaz.data?.varovani ?? []
  if (varovani.length === 0) return null
  return (
    <Alert color="orange" title="Upozornění (let můžete přesto založit)">
      <Stack gap={2}>
        {varovani.map((v) => (
          <Text key={v} fz="sm">
            {v}
          </Text>
        ))}
      </Stack>
    </Alert>
  )
}
