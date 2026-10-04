import { Badge, Group, Paper, Stack, Text } from '@mantine/core'
import type { ReactNode } from 'react'

import type { Let } from '../api/lety'
import { hhmm } from '../cas'

/** Výrazný rámeček kolem dvojice vleku, dokud kluzák i vlečná letí nebo čekají na start. */
export function SkupinaVleku({ kluzak, vlecna, children }: {
  kluzak: Let
  vlecna: Let
  children: ReactNode
}) {
  return (
    <Paper
      withBorder
      p={6}
      radius="md"
      style={{
        borderColor: 'var(--mantine-color-blue-6)',
        borderWidth: 2,
        background: 'var(--mantine-color-blue-light)',
      }}
    >
      <Group gap="xs" px={4} pb={6}>
        <Badge color="blue" variant="filled">
          ⇄ VLEK
        </Badge>
        <Text fz="sm" fw={600}>
          {kluzak.imatrikulace} + {vlecna.imatrikulace}
        </Text>
        {kluzak.cas_vzletu && (
          <Text fz="xs" c="dimmed">
            společný vzlet {hhmm(kluzak.cas_vzletu)}
          </Text>
        )}
      </Group>
      <Stack gap={6}>{children}</Stack>
    </Paper>
  )
}
