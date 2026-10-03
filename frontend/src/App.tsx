import { Badge, Card, Container, Group, Stack, Text, Title } from '@mantine/core'
import { useInterval } from '@mantine/hooks'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'

import { nactiHealth } from './api/health'

function casUtc(datum: Date) {
  return datum.toISOString().slice(11, 19)
}

function HodinyUtc() {
  const [ted, setTed] = useState(() => new Date())
  useInterval(() => setTed(new Date()), 1000, { autoInvoke: true })
  return (
    <Text ff="monospace" fz="xl" fw={600}>
      UTC {casUtc(ted)}
    </Text>
  )
}

function StavServeru() {
  const { data, isPending, isError } = useQuery({
    queryKey: ['health'],
    queryFn: nactiHealth,
    refetchInterval: 10_000,
  })

  if (isPending) return <Badge color="gray">Načítám…</Badge>
  if (isError || data.status !== 'ok') return <Badge color="red">Server nedostupný</Badge>
  return (
    <Group gap="xs">
      <Badge color="green">Server v pořádku</Badge>
      <Text c="dimmed" fz="sm">
        verze {data.verze}
      </Text>
    </Group>
  )
}

export default function App() {
  return (
    <Container size="sm" py="xl">
      <Stack gap="lg">
        <Group justify="space-between" align="center">
          <Title order={1}>LKKL Log</Title>
          <HodinyUtc />
        </Group>
        <Card withBorder padding="lg">
          <Stack gap="sm">
            <Text>Evidence letů aeroklubu – aplikace se právě staví.</Text>
            <StavServeru />
          </Stack>
        </Card>
      </Stack>
    </Container>
  )
}
