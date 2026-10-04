import { Text } from '@mantine/core'
import { useInterval } from '@mantine/hooks'
import { useState } from 'react'

export function HodinyUtc() {
  const [ted, setTed] = useState(() => new Date())
  useInterval(() => setTed(new Date()), 1000, { autoInvoke: true })
  return (
    <Text ff="monospace" fw={600} aria-label="Čas UTC">
      UTC {ted.toISOString().slice(11, 19)}
    </Text>
  )
}
