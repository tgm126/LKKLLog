import { Alert, Button, Container, Group, Loader, Stack, Switch, Table, Text, Title } from '@mantine/core'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate } from 'react-router'

import { KATEGORIE_LETADLA, type KartaLetadla, nactiLetadla } from '../api/letadla'
import { doba } from '../cas'
import { BARVA_STAVU } from '../stav'

const priznaky = (l: KartaLetadla) =>
  [!l.aktivni && 'neaktivní', l.vlecne && 'vlečné', l.soukrome && 'soukromé'].filter(Boolean).join(', ')

/** Stav termínů: problémové vyjmenované, jinak jen „v pořádku“. */
function StavTerminu({ l }: { l: KartaLetadla }) {
  const problemy = l.terminy.filter((t) => t.stav === 'pozor' || t.stav === 'chyba')
  return (
    <Stack gap={0}>
      {problemy.map((t) => (
        <Text key={t.id} fz="sm" c={BARVA_STAVU[t.stav]}>
          {t.nazev}{' '}
          <Text span fz="xs" c="dimmed">
            {t.text}
          </Text>
        </Text>
      ))}
      {problemy.length === 0 && (
        <Text fz="sm" c={l.terminy.length ? BARVA_STAVU.ok : 'dimmed'}>
          {l.terminy.length ? 'v pořádku' : 'bez termínů'}
        </Text>
      )}
      {l.chybi_denik && (
        <Text fz="xs" c="orange">
          chybí stav provozního deníku
        </Text>
      )}
    </Stack>
  )
}

/** Letadla: hustý seznam s náletem a stavem termínů; řádek otevře kartu letadla. */
export function Letadla() {
  const [vse, setVse] = useState(false)
  const letadla = useQuery({ queryKey: ['sprava', 'letadla', vse], queryFn: () => nactiLetadla(vse) })
  const navigate = useNavigate()

  return (
    <Container size="lg" pb="xl">
      <Stack gap="sm">
        <Group justify="space-between">
          <Title order={3}>Letadla</Title>
          <Button size="compact-sm" onClick={() => navigate('/letadla/nove')}>
            + Nové letadlo
          </Button>
        </Group>
        <Switch label="I neaktivní" checked={vse} onChange={(e) => setVse(e.currentTarget.checked)} />
        {letadla.isPending && <Loader size="sm" />}
        {letadla.isError && <Alert color="red">{letadla.error.message}</Alert>}
        {letadla.data && (
          <Table.ScrollContainer minWidth={640}>
            <Table fz="sm" verticalSpacing={4} horizontalSpacing="sm" highlightOnHover withTableBorder>
              <Table.Thead>
                <Table.Tr>
                  {['Letadlo', 'Kategorie', 'Nálet', 'Starty', 'Termíny'].map((n) => (
                    <Table.Th key={n} fz="xs" c="dimmed" fw={500}>
                      {n}
                    </Table.Th>
                  ))}
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {letadla.data.map((l) => (
                  <Table.Tr key={l.id} onClick={() => navigate(`/letadla/${l.id}`)} style={{ cursor: 'pointer' }}>
                    <Table.Td>
                      <Text span fz="sm" fw={500} c={l.aktivni ? undefined : 'dimmed'}>
                        {l.imatrikulace}
                      </Text>{' '}
                      <Text span fz="sm">
                        {l.typ}
                      </Text>
                      {priznaky(l) && (
                        <Text span fz="xs" c="dimmed">
                          {' '}
                          · {priznaky(l)}
                        </Text>
                      )}
                    </Table.Td>
                    <Table.Td>{KATEGORIE_LETADLA[l.kategorie] ?? l.kategorie}</Table.Td>
                    <Table.Td style={{ whiteSpace: 'nowrap' }}>{doba(l.nalet_min)}</Table.Td>
                    <Table.Td>{l.starty}</Table.Td>
                    <Table.Td>
                      <StavTerminu l={l} />
                    </Table.Td>
                  </Table.Tr>
                ))}
                {letadla.data.length === 0 && (
                  <Table.Tr>
                    <Table.Td colSpan={5} c="dimmed">
                      Žádná letadla.
                    </Table.Td>
                  </Table.Tr>
                )}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        )}
      </Stack>
    </Container>
  )
}
