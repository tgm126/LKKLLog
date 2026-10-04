import { Button, Group, Text } from '@mantine/core'
import { notifications } from '@mantine/notifications'
import type { QueryClient } from '@tanstack/react-query'

import { type Let, vratitZpet } from './api/lety'
import { jeLetovyDotaz } from './useLety'

/** Potvrzení akce s tlačítkem „Zpět“ na 10 sekund (pro omylem zmáčknuté tlačítko). */
export function oznamitSeZpet(let_: Let, zprava: string, klient: QueryClient) {
  const id = `zpet-${let_.id}-${let_.verze}`
  const vratit = async () => {
    notifications.hide(id)
    try {
      await vratitZpet(let_.id, let_.verze)
      notifications.show({ message: `${let_.imatrikulace}: akce vrácena.`, color: 'blue' })
    } catch (e) {
      notifications.show({ message: (e as Error).message, color: 'red' })
    }
    void klient.invalidateQueries({ predicate: jeLetovyDotaz })
  }
  notifications.show({
    id,
    color: 'green',
    autoClose: 10_000,
    message: (
      <Group justify="space-between" wrap="nowrap">
        <Text fz="sm">{zprava}</Text>
        <Button size="xs" variant="light" onClick={vratit} style={{ flexShrink: 0 }}>
          Zpět
        </Button>
      </Group>
    ),
  })
}
