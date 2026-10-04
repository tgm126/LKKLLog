import {
  ActionIcon,
  Alert,
  Badge,
  Button,
  Card,
  Container,
  Group,
  Loader,
  Stack,
  Text,
  Title,
} from '@mantine/core'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useState } from 'react'

import { type DenMesice, nactiMesic, type TypUzaverky, type Uzaverka } from '../api/uzaverky'
import { datumCasUtc, datumCesky, doba, nazevObdobi } from '../cas'
import { DetailUzaverky } from '../komponenty/DetailUzaverky'
import { UzavritDialog } from '../komponenty/UzavritDialog'

const iso = (d: Date) => d.toISOString().slice(0, 10)

function posunMesic(mesic: string, o: number) {
  const d = new Date(`${mesic}T12:00:00Z`)
  return iso(new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + o, 1)))
}

type Volba = { typ: TypUzaverky; obdobi: string }

function StavUzaverky({ u, zmeny }: { u: Uzaverka | null; zmeny: number }) {
  if (!u) return <Badge color="gray" variant="light">neuzavřeno</Badge>
  return (
    <Group gap={6}>
      <Badge color="green" variant="light">
        uzavřeno v{u.verze}
      </Badge>
      {zmeny > 0 && (
        <Badge color="orange" variant="filled">
          změny po uzávěrce: {zmeny}
        </Badge>
      )}
    </Group>
  )
}

/** Uzávěrky: dny měsíce se stavem uzavření, měsíční uzávěrka a změny po uzávěrce. */
export function Uzaverky() {
  const [tentoMesic] = useState(() => iso(new Date()).slice(0, 8) + '01')
  const [mesic, setMesic] = useState(tentoMesic)
  const [uzavrit, setUzavrit] = useState<Volba | null>(null)
  const [detail, setDetail] = useState<Volba | null>(null)
  const data = useQuery({
    queryKey: ['uzaverky', 'mesic', mesic],
    queryFn: () => nactiMesic(mesic),
    placeholderData: keepPreviousData,
    refetchOnWindowFocus: true,
  })
  const m = data.data

  const tlacitka = (typ: TypUzaverky, obdobi: string, u: Uzaverka | null, zmeny: number, smi: boolean) => (
    <Group gap="xs">
      {u && (
        <Button size="xs" variant="default" onClick={() => setDetail({ typ, obdobi })}>
          Detail
        </Button>
      )}
      {smi && (!u || zmeny > 0) && (
        <Button size="xs" onClick={() => setUzavrit({ typ, obdobi })}>
          {u ? 'Přepočítat' : 'Uzavřít'}
        </Button>
      )}
    </Group>
  )

  const den = (d: DenMesice) => (
    <Card key={d.den} withBorder padding="sm">
      <Group justify="space-between" wrap="wrap" gap="xs">
        <Stack gap={2}>
          <Text fw={600} tt="capitalize">
            {datumCesky(d.den)}
          </Text>
          <Text fz="sm" c="dimmed">
            {d.lety} {d.lety === 1 ? 'let' : d.lety >= 2 && d.lety <= 4 ? 'lety' : 'letů'} ·{' '}
            {doba(d.minuty)}
            {d.uzaverka && ` · ${datumCasUtc(d.uzaverka.kdy)}, ${d.uzaverka.uzavrel}`}
          </Text>
          <Group gap={6}>
            <StavUzaverky u={d.uzaverka} zmeny={d.zmeny} />
            {d.neukonceno > 0 && (
              <Badge color="red" variant="light">
                neukončeno: {d.neukonceno}
              </Badge>
            )}
          </Group>
        </Stack>
        {tlacitka('den', d.den, d.uzaverka, d.zmeny, d.smi_uzavrit)}
      </Group>
    </Card>
  )

  return (
    <Container size="sm" pb="xl">
      <Stack gap="md">
        <Group justify="space-between">
          <ActionIcon variant="default" size="lg" aria-label="Předchozí měsíc" onClick={() => setMesic(posunMesic(mesic, -1))}>
            ‹
          </ActionIcon>
          <Title order={2} tt="capitalize">
            {nazevObdobi('mesic', mesic)}
          </Title>
          <ActionIcon
            variant="default"
            size="lg"
            aria-label="Další měsíc"
            disabled={mesic >= tentoMesic}
            onClick={() => setMesic(posunMesic(mesic, 1))}
          >
            ›
          </ActionIcon>
        </Group>

        {data.isPending && <Loader />}
        {data.isError && <Alert color="red">{data.error.message}</Alert>}
        {m && (
          <>
            <Card withBorder padding="sm" bg="var(--mantine-color-blue-light)">
              <Group justify="space-between" wrap="wrap" gap="xs">
                <Stack gap={2}>
                  <Text fw={700}>Měsíční uzávěrka</Text>
                  {m.uzaverka ? (
                    <Text fz="sm" c="dimmed">
                      {datumCasUtc(m.uzaverka.kdy)}, {m.uzaverka.uzavrel}
                    </Text>
                  ) : (
                    <Text fz="sm" c="dimmed">
                      {m.skoncil ? 'Měsíc skončil, čeká na uzavření.' : 'Měsíc ještě běží.'}
                    </Text>
                  )}
                  <StavUzaverky u={m.uzaverka} zmeny={m.zmeny} />
                </Stack>
                {tlacitka('mesic', m.mesic, m.uzaverka, m.zmeny, m.smi_uzavrit && m.skoncil)}
              </Group>
            </Card>

            <Title order={4}>Dny s lety</Title>
            {m.dny.length === 0 && <Text c="dimmed">V tomto měsíci se nelétalo.</Text>}
            {m.dny.map(den)}
          </>
        )}
      </Stack>

      {uzavrit && (
        <UzavritDialog typ={uzavrit.typ} obdobi={uzavrit.obdobi} onZavrit={() => setUzavrit(null)} />
      )}
      {detail && (
        <DetailUzaverky typ={detail.typ} obdobi={detail.obdobi} onZavrit={() => setDetail(null)} />
      )}
    </Container>
  )
}
