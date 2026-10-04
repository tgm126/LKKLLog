import { Alert, Button, Card, Group, Loader, Stack, Text, Title } from '@mantine/core'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router'

import { type Kontrola, kontrolaPosadky, type KontrolaPosadky, nactiRozletanost } from '../api/licence'

const BARVA: Record<Kontrola['stav'], string> = {
  ok: 'green',
  pozor: 'orange',
  chyba: 'red',
  info: 'gray',
}
const ZNAK: Record<Kontrola['stav'], string> = { ok: '✓', pozor: '!', chyba: '✗', info: 'i' }

/** Přehled licencí, medicalu a rozlétanosti pilota (Můj nálet). */
export function Rozletanost() {
  const dotaz = useQuery({ queryKey: ['rozletanost'], queryFn: nactiRozletanost })
  const d = dotaz.data
  if (dotaz.isPending) return <Loader size="sm" />
  if (!d?.zobrazit) {
    return (
      <Group justify="space-between">
        <Text fz="sm" c="dimmed">
          Licence a medical si můžete zadat už teď; hlídání rozlétanosti zapne admin.
        </Text>
        <Button component={Link} to="/licence" size="xs" variant="light">
          Licence a medical
        </Button>
      </Group>
    )
  }
  return (
    <Stack gap="xs">
      <Group justify="space-between">
        <Title order={4}>Licence a rozlétanost</Title>
        <Button component={Link} to="/licence" size="xs" variant="light">
          Upravit licence a medical
        </Button>
      </Group>
      {!d.hlidani && (
        <Alert color="gray" p="xs">
          Hlídání je v Nastavení provozu vypnuté – tento přehled teď vidí jen admin.
        </Alert>
      )}
      {d.kontroly.map((k, i) => (
        <Card
          key={i}
          withBorder
          padding="xs"
          style={{ borderLeft: `4px solid var(--mantine-color-${BARVA[k.stav]}-6)` }}
        >
          <Group justify="space-between" wrap="nowrap" align="flex-start">
            <Text fz="sm" fw={600}>
              <Text span c={BARVA[k.stav]} fw={800}>
                {ZNAK[k.stav]}
              </Text>{' '}
              {k.nazev.startsWith(k.oblast) ? k.nazev : `${k.oblast} · ${k.nazev}`}
            </Text>
            <Text fz="sm" ta="right">
              {k.text}
            </Text>
          </Group>
          {k.podrobnosti.map((p) => (
            <Text key={p} fz="xs" c="dimmed">
              {p}
            </Text>
          ))}
        </Card>
      ))}
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
