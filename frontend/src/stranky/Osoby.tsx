import { Alert, Button, Container, Group, Loader, Stack, Switch, Table, Text, TextInput, Title } from '@mantine/core'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate } from 'react-router'

import { nactiOsoby, type RadekOsoby } from '../api/osoby'
import { BARVA_STAVU, TEXT_STAVU } from '../stav'


const priznaky = (o: RadekOsoby) =>
  [!o.aktivni && 'neaktivní', o.externi && 'externí', o.testovaci && 'testovací'].filter(Boolean).join(', ')

/** Osoby: hustý seznam se stavem dokladů; řádek otevře kartu osoby. */
export function Osoby() {
  const osoby = useQuery({ queryKey: ['sprava', 'osoby'], queryFn: nactiOsoby })
  const navigate = useNavigate()
  const [hledat, setHledat] = useState('')
  const [jenProblemy, setJenProblemy] = useState(false)
  const [neaktivni, setNeaktivni] = useState(false)

  const seznam = (osoby.data ?? []).filter(
    (o) =>
      (neaktivni || o.aktivni) &&
      (!jenProblemy || o.stav === 'pozor' || o.stav === 'chyba') &&
      (!hledat || `${o.jmeno} ${o.email ?? ''}`.toLowerCase().includes(hledat.toLowerCase())),
  )

  return (
    <Container size="lg" pb="xl">
      <Stack gap="sm">
        <Group justify="space-between">
          <Title order={3}>Osoby</Title>
          <Button size="compact-sm" onClick={() => navigate('/osoby/nova')}>
            + Nová osoba
          </Button>
        </Group>
        <Group gap="md">
          <TextInput
            placeholder="Hledat jméno nebo e-mail"
            value={hledat}
            onChange={(e) => setHledat(e.currentTarget.value)}
            w={260}
          />
          <Switch label="Jen s problémem" checked={jenProblemy} onChange={(e) => setJenProblemy(e.currentTarget.checked)} />
          <Switch label="I neaktivní" checked={neaktivni} onChange={(e) => setNeaktivni(e.currentTarget.checked)} />
        </Group>
        {osoby.isPending && <Loader size="sm" />}
        {osoby.isError && <Alert color="red">{osoby.error.message}</Alert>}
        {osoby.data && (
          <Table.ScrollContainer minWidth={640}>
            <Table fz="sm" verticalSpacing={4} horizontalSpacing="sm" highlightOnHover withTableBorder>
              <Table.Thead>
                <Table.Tr>
                  {['Jméno', 'Průkazy', 'Role', 'Stav dokladů'].map((n) => (
                    <Table.Th key={n} fz="xs" c="dimmed" fw={500}>
                      {n}
                    </Table.Th>
                  ))}
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {seznam.map((o) => (
                  <Table.Tr key={o.id} onClick={() => navigate(`/osoby/${o.id}`)} style={{ cursor: 'pointer' }}>
                    <Table.Td>
                      <Text span fz="sm" fw={500} c={o.aktivni ? undefined : 'dimmed'}>
                        {o.jmeno}
                      </Text>
                      {priznaky(o) && (
                        <Text span fz="xs" c="dimmed">
                          {' '}
                          · {priznaky(o)}
                        </Text>
                      )}
                    </Table.Td>
                    <Table.Td>{o.prukazy.join(', ')}</Table.Td>
                    <Table.Td>{o.role.join(', ')}</Table.Td>
                    <Table.Td>
                      {o.stav && (
                        <Text span fz="sm" c={BARVA_STAVU[o.stav]}>
                          {TEXT_STAVU[o.stav]}
                          {o.problemy.length > 0 && (
                            <Text span fz="xs" c="dimmed">
                              {' '}
                              · {o.problemy.length} {o.problemy.length === 1 ? 'problém' : o.problemy.length < 5 ? 'problémy' : 'problémů'}
                            </Text>
                          )}
                        </Text>
                      )}
                    </Table.Td>
                  </Table.Tr>
                ))}
                {seznam.length === 0 && (
                  <Table.Tr>
                    <Table.Td colSpan={4} c="dimmed">
                      Nikdo neodpovídá filtru.
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
