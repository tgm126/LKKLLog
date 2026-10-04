import { Alert, Anchor, Badge, Card, Group, Loader, Modal, Stack, Text, Title } from '@mantine/core'
import { useQuery } from '@tanstack/react-query'

import { nactiDetail, odkazExportuUzaverky, type TypUzaverky } from '../api/uzaverky'
import { datumCasUtc, doba, hhmm, nazevObdobi } from '../cas'
import { useNazvy } from '../nazvy'
import { useJa } from '../useJa'
import { useCiselniky } from '../useLety'
import { SouhrnUzaverky } from './SouhrnUzaverky'

const sZnamenkem = (x: number, f: (x: number) => string = String) =>
  x > 0 ? `+${f(x)}` : x < 0 ? `−${f(-x)}` : '0'

/** Verze uzávěrky, změny po ní (o kolik se liší součty, kdo, co a proč) a uložený souhrn. */
export function DetailUzaverky({
  typ,
  obdobi,
  onZavrit,
}: {
  typ: TypUzaverky
  obdobi: string
  onZavrit: () => void
}) {
  const { data: ja } = useJa()
  const { data: c } = useCiselniky()
  const n = useNazvy(c)
  const detail = useQuery({
    queryKey: ['uzaverky', 'detail', typ, obdobi],
    queryFn: () => nactiDetail(typ, obdobi),
  })
  const smiExport = !!(ja?.role?.ucetni || ja?.role?.admin)
  const d = detail.data

  return (
    <Modal opened onClose={onZavrit} title={`Uzávěrka: ${nazevObdobi(typ, obdobi)}`} size="lg">
      {detail.isPending && <Loader />}
      {detail.isError && <Alert color="red">{detail.error.message}</Alert>}
      {d && (
        <Stack>
          {d.rozdil && (
            <Alert color="orange" title={`Změny po uzávěrce (${d.lety.length})`}>
              Oproti uloženému souhrnu: lety {sZnamenkem(d.rozdil.celkem.lety)}, doba{' '}
              {sZnamenkem(d.rozdil.celkem.minuty, (m) => doba(m))}, přistání{' '}
              {sZnamenkem(d.rozdil.celkem.pristani ?? 0)}, vleky {sZnamenkem(d.rozdil.celkem.vlek)}
              {Object.entries(d.rozdil.starty)
                .filter(([, x]) => x !== 0)
                .map(([z, x]) => `, starty ${n.zpusob(z).toLowerCase()} ${sZnamenkem(x)}`)
                .join('')}
              .
            </Alert>
          )}
          {d.lety.map((l) => (
            <Card key={l.id} withBorder padding="xs">
              <Group justify="space-between">
                <Text fw={600}>
                  {l.imatrikulace} {hhmm(l.cas_vzletu)}–{hhmm(l.cas_pristani)}
                </Text>
                <Text fz="sm">
                  {l.stav === 'zrusen' ? <Badge color="gray">zrušen</Badge> : doba(l.doba_uctovana_min)}
                </Text>
              </Group>
              {l.zaznamy.map((z, i) => (
                <Stack key={i} gap={0} mt={4}>
                  <Text fz="sm">
                    {z.akce} · {z.kdo}
                    {z.duvod && ` · ${z.duvod}`}
                  </Text>
                  <Text fz="xs" c="dimmed">
                    {datumCasUtc(z.kdy)}
                    {z.poznamka && ` · „${z.poznamka}“`}
                  </Text>
                  {Object.entries(z.zmeny).map(([pole, h]) =>
                    Array.isArray(h) && h.length === 2 ? (
                      <Text key={pole} fz="xs">
                        {pole}: <s>{String(h[0])}</s> → <b>{String(h[1])}</b>
                      </Text>
                    ) : null,
                  )}
                </Stack>
              ))}
            </Card>
          ))}

          <Title order={5}>Verze</Title>
          {d.verze.map((u) => (
            <Group key={u.id} justify="space-between" wrap="nowrap">
              <Text fz="sm" c={u.platna ? undefined : 'dimmed'}>
                v{u.verze} · {datumCasUtc(u.kdy)} · {u.uzavrel}
                {!u.platna && ' (znovu otevřeno)'}
              </Text>
              {smiExport && (
                <Anchor fz="sm" href={odkazExportuUzaverky(u.id)}>
                  Excel
                </Anchor>
              )}
            </Group>
          ))}

          {d.souhrn ? (
            <>
              <Title order={5}>Uložený souhrn (v{d.verze.find((u) => u.platna)?.verze})</Title>
              <SouhrnUzaverky souhrn={d.souhrn} uplny />
            </>
          ) : (
            <Text c="dimmed">Uzávěrka byla znovu otevřena, žádná verze teď neplatí.</Text>
          )}
        </Stack>
      )}
    </Modal>
  )
}
