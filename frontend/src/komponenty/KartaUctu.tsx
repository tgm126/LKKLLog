import { Center, Paper, Stack, Text, Title } from '@mantine/core'
import type { ReactNode } from 'react'

/** Rámeček pro přihlášení, zapomenuté heslo a nastavení hesla. */
export function KartaUctu({
  nadpis,
  popis,
  children,
}: {
  nadpis: string
  popis?: string
  children: ReactNode
}) {
  return (
    <Center py="xl" px="md">
      <Paper withBorder shadow="sm" p="xl" w="100%" maw={420}>
        <Stack gap="md">
          <div>
            <Title order={2}>{nadpis}</Title>
            {popis && (
              <Text c="dimmed" fz="sm" mt={4}>
                {popis}
              </Text>
            )}
          </div>
          {children}
        </Stack>
      </Paper>
    </Center>
  )
}
