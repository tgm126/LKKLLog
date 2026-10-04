import { Alert, Container, Grid, Loader, NavLink, Select, Stack, Text, Title } from '@mantine/core'
import { useMediaQuery } from '@mantine/hooks'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useSearchParams } from 'react-router'

import { nactiSeznamCiselniku, type RadekCiselniku } from '../api/ciselniky'
import { TabulkaCiselniku } from '../komponenty/TabulkaCiselniku'

/** Číselníky (jen admin): seznamy hodnot pro karty osob a letadel. */
export function Ciselniky() {
  // Klíč se liší od ['ciselniky'] – to jsou data pro průvodce letem (useCiselniky).
  const seznam = useQuery({ queryKey: ['sprava-ciselniky'], queryFn: nactiSeznamCiselniku })
  const [parametry, setParametry] = useSearchParams()
  const mobil = useMediaQuery('(max-width: 48em)')
  const [rodic, setRodic] = useState<RadekCiselniku | null>(null)
  // Podřízené číselníky (kvalifikace, úlohy) se ukazují pod nadřazenou položkou.
  const hlavni = (seznam.data ?? []).filter((c) => !c.rodic)
  const klic = parametry.get('c') ?? hlavni[0]?.klic ?? null
  const aktualni = seznam.data?.find((c) => c.klic === klic)
  const vyber = (k: string | null) => {
    setRodic(null)
    if (k) setParametry({ c: k })
  }

  const detiNazev = (k: string) => seznam.data?.find((c) => c.klic === k)?.nazev ?? ''
  const deti = aktualni?.deti

  return (
    <Container size="lg" pb="xl">
      <Stack gap="sm">
        <Title order={3}>Číselníky</Title>
        {seznam.isPending && <Loader size="sm" />}
        {seznam.isError && <Alert color="red">{seznam.error.message}</Alert>}
        {seznam.data && (
          <Grid gap="md">
            <Grid.Col span={{ base: 12, sm: 3 }}>
              {mobil ? (
                <Select
                  data={hlavni.map((c) => ({ value: c.klic, label: c.nazev }))}
                  value={klic}
                  onChange={vyber}
                  allowDeselect={false}
                />
              ) : (
                <Stack gap={0}>
                  {hlavni.map((c) => (
                    <NavLink
                      key={c.klic}
                      label={c.nazev}
                      rightSection={
                        <Text fz="xs" c="dimmed">
                          {c.pocet}
                        </Text>
                      }
                      active={c.klic === klic}
                      onClick={() => vyber(c.klic)}
                      py={4}
                    />
                  ))}
                </Stack>
              )}
            </Grid.Col>
            <Grid.Col span={{ base: 12, sm: 9 }}>
              {klic && (
                <Stack gap="md">
                  <TabulkaCiselniku
                    key={klic}
                    klic={klic}
                    vybrany={rodic?.id}
                    onVyber={deti ? setRodic : undefined}
                  />
                  {deti && !rodic && (
                    <Text fz="xs" c="dimmed">
                      Klikněte na řádek a ukážou se jeho {detiNazev(deti).toLowerCase()}.
                    </Text>
                  )}
                  {deti && rodic && (
                    <TabulkaCiselniku
                      key={`${deti}-${rodic.id}`}
                      klic={deti}
                      rodic={rodic.id}
                      nadpis={`${detiNazev(deti)} – ${String(rodic.hodnoty.nazev)}`}
                    />
                  )}
                </Stack>
              )}
            </Grid.Col>
          </Grid>
        )}
      </Stack>
    </Container>
  )
}
