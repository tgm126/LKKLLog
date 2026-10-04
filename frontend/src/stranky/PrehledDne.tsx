import { Affix, Alert, Button, Container, Group, Loader, Stack, Text, Title } from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { type Let, vzlet } from '../api/lety'
import { datumCesky, doba, hhmm } from '../cas'
import { DetailLetu } from '../komponenty/DetailLetu'
import { KartaLetu } from '../komponenty/KartaLetu'
import { NovyLet } from '../komponenty/NovyLet'
import { OpravaLetu } from '../komponenty/OpravaLetu'
import { PristaniDialog } from '../komponenty/PristaniDialog'
import { ZruseniDialog } from '../komponenty/ZruseniDialog'
import { PREHLED_KLIC, useCiselniky, usePrehled, useServerovyCas } from '../useLety'
import { oznamitSeZpet } from '../zpet'

export function PrehledDne() {
  const { data: prehled, isPending, isError, error } = usePrehled()
  useCiselniky() // načte číselníky dopředu, ať je průvodce novým letem hned připravený
  const ted = useServerovyCas(prehled?.ted)
  const klient = useQueryClient()
  const [novy, setNovy] = useState(false)
  const [vychozi, setVychozi] = useState<Let | undefined>()
  const [pristani, setPristani] = useState<Let | null>(null)
  const [zruseni, setZruseni] = useState<Let | null>(null)
  const [detailId, setDetailId] = useState<number | null>(null)
  const [opravaId, setOpravaId] = useState<number | null>(null)

  const start = useMutation({
    mutationFn: (l: Let) => vzlet(l.id),
    onSuccess: (l) =>
      oznamitSeZpet(l, `${l.imatrikulace}${l.vlek ? ` + ${l.vlek}` : ''} vzlétl.`, klient),
    onError: (e) => notifications.show({ message: e.message, color: 'red' }),
    onSettled: () => klient.invalidateQueries({ queryKey: PREHLED_KLIC }),
  })

  if (isPending) {
    return (
      <Container py="xl">
        <Loader />
      </Container>
    )
  }
  if (isError) {
    return (
      <Container py="xl">
        <Alert color="red">Přehled se nepodařilo načíst: {error.message}</Alert>
      </Container>
    )
  }

  const veVzduchu = prehled.lety.filter((l) => l.stav === 've_vzduchu')
  const pripravene = prehled.lety.filter((l) => l.stav === 'pripraven')
  const ukoncene = prehled.lety.filter((l) => l.stav === 'ukoncen' || l.stav === 'zrusen')
  const nalet = ukoncene.reduce((s, l) => s + (l.doba_uctovana_min ?? 0), 0)

  // Detail a oprava berou vždy aktuální verzi letu z přehledu (obnovuje se každých 10 s).
  const detail = prehled.lety.find((l) => l.id === detailId)
  const oprava = prehled.lety.find((l) => l.id === opravaId)

  const karta = (l: Let) => (
    <KartaLetu
      key={l.id}
      let_={l}
      ted={ted}
      konecSoumraku={prehled.konec_soumraku}
      pracuje={start.isPending && start.variables?.id === l.id}
      onVzlet={() => start.mutate(l)}
      onPristani={() => setPristani(l)}
      onZrusit={() => setZruseni(l)}
      onDetail={() => setDetailId(l.id)}
      onOpravit={() => setOpravaId(l.id)}
      onDalsi={() => {
        setVychozi(l)
        setNovy(true)
      }}
    />
  )

  return (
    <Container size="sm" pb={100}>
      <Stack gap="lg">
        <div>
          <Title order={2} tt="capitalize">
            {datumCesky(prehled.den)}
          </Title>
          <Text c="dimmed" fz="sm">
            Západ slunce {hhmm(prehled.zapad_slunce)} · konec soumraku{' '}
            {hhmm(prehled.konec_soumraku)} UTC
          </Text>
        </div>

        <Stack gap="xs">
          <Title order={4}>Ve vzduchu ({veVzduchu.length})</Title>
          {veVzduchu.length === 0 && <Text c="dimmed">Nikdo nelétá.</Text>}
          {veVzduchu.map(karta)}
        </Stack>

        {pripravene.length > 0 && (
          <Stack gap="xs">
            <Title order={4}>Připravené ({pripravene.length})</Title>
            {pripravene.map(karta)}
          </Stack>
        )}

        <Stack gap="xs">
          <Group justify="space-between">
            <Title order={4}>Ukončené ({ukoncene.filter((l) => l.stav === 'ukoncen').length})</Title>
            <Text fz="sm" c="dimmed">
              celkem {doba(nalet)}
            </Text>
          </Group>
          {ukoncene.length === 0 && <Text c="dimmed">Zatím nic.</Text>}
          {[...ukoncene].reverse().map(karta)}
        </Stack>
      </Stack>

      <Affix position={{ bottom: 16, left: 16, right: 16 }}>
        <Container size="sm" p={0}>
          <Button size="xl" fullWidth onClick={() => setNovy(true)} style={{ boxShadow: 'var(--mantine-shadow-md)' }}>
            + NOVÝ LET
          </Button>
        </Container>
      </Affix>

      {novy && (
        <NovyLet
          key={vychozi?.id ?? 'novy'}
          otevreno
          onZavrit={() => {
            setNovy(false)
            setVychozi(undefined)
          }}
          lety={prehled.lety}
          ted={ted}
          vychozi={vychozi}
        />
      )}
      <PristaniDialog let_={pristani} onZavrit={() => setPristani(null)} />
      <ZruseniDialog let_={zruseni} onZavrit={() => setZruseni(null)} />
      <DetailLetu
        let_={detail ?? null}
        onZavrit={() => setDetailId(null)}
        onOpravit={() => {
          setOpravaId(detailId)
          setDetailId(null)
        }}
        onZrusit={() => {
          setZruseni(detail ?? null)
          setDetailId(null)
        }}
      />
      {oprava && (
        <OpravaLetu
          key={`${oprava.id}-${oprava.verze}`}
          let_={oprava}
          lety={prehled.lety}
          ted={ted}
          onZavrit={() => setOpravaId(null)}
        />
      )}
    </Container>
  )
}
