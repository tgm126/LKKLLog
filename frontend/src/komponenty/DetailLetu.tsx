import { Badge, Button, Group, Loader, Modal, Stack, Table, Text, Timeline } from '@mantine/core'
import { useQuery } from '@tanstack/react-query'

import { type Let, nactiHistorii } from '../api/lety'
import { doba, hhmmss } from '../cas'
import { KATEGORIE_LETU, useNazvy } from '../nazvy'
import { useCiselniky } from '../useLety'

function Radek({ nazev, hodnota }: { nazev: string; hodnota: React.ReactNode }) {
  return (
    <Table.Tr>
      <Table.Td c="dimmed" w="40%">
        {nazev}
      </Table.Td>
      <Table.Td>{hodnota}</Table.Td>
    </Table.Tr>
  )
}

const datumCas = (iso: string | null) =>
  iso
    ? `${new Date(iso).toLocaleDateString('cs-CZ', { timeZone: 'UTC' })} ${hhmmss(iso)} UTC`
    : '–'

/** Detail letu se všemi údaji a historií změn (kdo, kdy, co a proč). */
export function DetailLetu({
  let_,
  onZavrit,
  onOpravit,
  onZrusit,
}: {
  let_: Let | null
  onZavrit: () => void
  onOpravit: () => void
  onZrusit: () => void
}) {
  const { data: c } = useCiselniky()
  const n = useNazvy(c)
  const historie = useQuery({
    queryKey: ['historie', let_?.id, let_?.verze],
    queryFn: () => nactiHistorii(let_!.id),
    enabled: let_ !== null,
  })
  if (!let_) return null
  const lze = let_.muze_ovladat && let_.stav !== 'zrusen'

  return (
    <Modal opened onClose={onZavrit} title={`Let ${let_.imatrikulace}`} size="lg">
      <Stack>
        <Table withRowBorders={false} verticalSpacing={4}>
          <Table.Tbody>
            <Radek nazev="Letadlo" hodnota={`${let_.imatrikulace} (${let_.typ})`} />
            <Radek
              nazev="Typ letu"
              hodnota={`${KATEGORIE_LETU[let_.kategorie]} · ${n.ucel(let_.ucel).toLowerCase()}`}
            />
            <Radek
              nazev="Posádka"
              hodnota={let_.posadka.map((p) => `${p.jmeno} (${n.funkce(p.funkce)})`).join(', ')}
            />
            {let_.pocet_hostu > 0 && <Radek nazev="Hosté" hodnota={let_.pocet_hostu} />}
            <Radek nazev="Platí" hodnota={let_.plati_aeroklub ? 'Aeroklub' : let_.platce} />
            <Radek nazev="Úloha" hodnota={let_.uloha ?? '–'} />
            {let_.zpusob_vzletu !== 'vlastni' && (
              <Radek nazev="Způsob vzletu" hodnota={n.zpusob(let_.zpusob_vzletu)} />
            )}
            <Radek nazev="Vzlet" hodnota={`${let_.misto_vzletu} · ${datumCas(let_.cas_vzletu)}`} />
            <Radek
              nazev="Přistání"
              hodnota={
                let_.cas_pristani
                  ? `${let_.misto_pristani} · ${datumCas(let_.cas_pristani)}`
                  : '–'
              }
            />
            <Radek nazev="Doba" hodnota={doba(let_.doba_uctovana_min)} />
            {let_.pocet_tg > 0 && <Radek nazev="Touch-and-go" hodnota={let_.pocet_tg} />}
            <Radek nazev="Založil" hodnota={let_.zalozil} />
            {let_.stav === 'zrusen' && (
              <Radek nazev="Zrušen" hodnota={<Badge color="gray">{n.duvod(let_.duvod_zruseni)}</Badge>} />
            )}
          </Table.Tbody>
        </Table>

        {lze && (
          <Group grow>
            <Button variant="default" onClick={onOpravit}>
              Opravit…
            </Button>
            <Button variant="default" color="red" onClick={onZrusit}>
              Zrušit let…
            </Button>
          </Group>
        )}

        <Text fw={600}>Historie změn</Text>
        {historie.isPending && <Loader size="sm" />}
        {historie.data && (
          <Timeline bulletSize={14} lineWidth={2}>
            {historie.data.map((z, i) => (
              <Timeline.Item key={i} title={`${z.akce} · ${z.kdo}`}>
                <Text fz="xs" c="dimmed">
                  {datumCas(z.kdy)}
                  {z.duvod && ` · ${z.duvod}`}
                </Text>
                {z.poznamka && <Text fz="sm">„{z.poznamka}“</Text>}
                {(z.akce === 'Oprava' || z.akce === 'Vráceno tlačítkem Zpět') &&
                  Object.entries(z.zmeny).map(([pole, hodnoty]) =>
                    Array.isArray(hodnoty) && hodnoty.length === 2 ? (
                      <Text key={pole} fz="sm">
                        {pole}: <s>{String(hodnoty[0])}</s> → <b>{String(hodnoty[1])}</b>
                      </Text>
                    ) : null,
                  )}
              </Timeline.Item>
            ))}
          </Timeline>
        )}
      </Stack>
    </Modal>
  )
}
