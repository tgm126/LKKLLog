import { Affix, Alert, Badge, Button, Container, Group, Loader, Stack, Text, Title } from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { type Let, touchAndGo, vzlet } from '../api/lety'
import { datumCesky, doba, hhmm } from '../cas'
import { DetailLetu } from '../komponenty/DetailLetu'
import { DetailUzaverky } from '../komponenty/DetailUzaverky'
import { KartaLetu } from '../komponenty/KartaLetu'
import { NovyLet } from '../komponenty/NovyLet'
import { OpravaLetu } from '../komponenty/OpravaLetu'
import { PristaniDialog } from '../komponenty/PristaniDialog'
import { SkupinaVleku } from '../komponenty/SkupinaVleku'
import { UzavritDialog } from '../komponenty/UzavritDialog'
import { ZruseniDialog } from '../komponenty/ZruseniDialog'
import { jeLetovyDotaz, useCiselniky, usePrehled, useServerovyCas } from '../useLety'
import { seskupitVleky } from '../vleky'
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
  const [uzavrit, setUzavrit] = useState(false)
  const [detailUzaverky, setDetailUzaverky] = useState(false)

  const start = useMutation({
    mutationFn: (l: Let) => vzlet(l.id),
    onSuccess: (l) =>
      oznamitSeZpet(l, `${l.imatrikulace}${l.vlek ? ` + ${l.vlek}` : ''} vzlétl.`, klient),
    onError: (e) => notifications.show({ message: e.message, color: 'red' }),
    onSettled: () => klient.invalidateQueries({ predicate: jeLetovyDotaz }),
  })

  const tg = useMutation({
    mutationFn: (l: Let) => touchAndGo(l.id),
    onSuccess: (l) => oznamitSeZpet(l, `${l.imatrikulace}: touch-and-go (${l.pocet_tg}).`, klient),
    onError: (e) => notifications.show({ message: e.message, color: 'red' }),
    onSettled: () => klient.invalidateQueries({ predicate: jeLetovyDotaz }),
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
  const uz = prehled.uzaverka

  // Detail a oprava berou vždy aktuální verzi letu z přehledu (obnovuje se každých 10 s).
  const detail = prehled.lety.find((l) => l.id === detailId)
  const oprava = prehled.lety.find((l) => l.id === opravaId)

  const karta = (l: Let) => (
    <KartaLetu
      key={l.id}
      let_={l}
      ted={ted}
      konecSoumraku={prehled.konec_soumraku}
      pracuje={
        (start.isPending && start.variables?.id === l.id) ||
        (tg.isPending && tg.variables?.id === l.id)
      }
      onVzlet={() => start.mutate(l)}
      onTg={() => tg.mutate(l)}
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

  // Dvojice vleku (kluzák + vlečná) ve společném výrazném rámečku.
  const polozka = (p: Let | [Let, Let]) =>
    Array.isArray(p) ? (
      <SkupinaVleku key={`vlek-${p[0].id}`} kluzak={p[0]} vlecna={p[1]}>
        {karta(p[0])}
        {karta(p[1])}
      </SkupinaVleku>
    ) : (
      karta(p)
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
          {(uz.uzaverka || uz.smi_uzavrit || uz.mesic_uzavren) && (
            <Group gap="xs" mt={6}>
              {uz.uzaverka && (
                <Badge
                  color="green"
                  variant="light"
                  style={{ cursor: 'pointer' }}
                  onClick={() => setDetailUzaverky(true)}
                >
                  den uzavřen v{uz.uzaverka.verze} · {hhmm(uz.uzaverka.kdy)} · {uz.uzaverka.uzavrel}
                </Badge>
              )}
              {uz.mesic_uzavren && (
                <Badge color="green" variant="light">
                  měsíc uzavřen
                </Badge>
              )}
              {uz.zmeny > 0 && (
                <Badge color="orange" style={{ cursor: 'pointer' }} onClick={() => setDetailUzaverky(true)}>
                  změny po uzávěrce: {uz.zmeny}
                </Badge>
              )}
              {uz.smi_uzavrit && (!uz.uzaverka || uz.zmeny > 0) && (
                <Button size="compact-sm" variant="light" onClick={() => setUzavrit(true)}>
                  {uz.uzaverka ? 'Přepočítat' : 'Uzavřít den'}
                </Button>
              )}
            </Group>
          )}
        </div>

        <Stack gap="xs">
          <Title order={4}>Ve vzduchu ({veVzduchu.length})</Title>
          {veVzduchu.length === 0 && <Text c="dimmed">Nikdo nelétá.</Text>}
          {seskupitVleky(veVzduchu).map(polozka)}
        </Stack>

        {pripravene.length > 0 && (
          <Stack gap="xs">
            <Title order={4}>Připravené ({pripravene.length})</Title>
            {seskupitVleky(pripravene).map(polozka)}
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
      {uzavrit && (
        <UzavritDialog typ="den" obdobi={prehled.den} onZavrit={() => setUzavrit(false)} />
      )}
      {detailUzaverky && (
        <DetailUzaverky typ="den" obdobi={prehled.den} onZavrit={() => setDetailUzaverky(false)} />
      )}
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
