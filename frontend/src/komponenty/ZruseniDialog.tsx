import { Button, Modal, Stack, Text } from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { useMutation, useQueryClient } from '@tanstack/react-query'

import { type Let, zrusitLet } from '../api/lety'
import { PREHLED_KLIC, useCiselniky } from '../useLety'

/** Zrušení letu – důvod se vybírá z nabídky, let se nesmaže. */
export function ZruseniDialog({ let_, onZavrit }: { let_: Let | null; onZavrit: () => void }) {
  const { data: c } = useCiselniky()
  const klient = useQueryClient()
  const zruseni = useMutation({
    mutationFn: (duvod: string) => zrusitLet(let_!.id, duvod),
    onSuccess: (l) => notifications.show({ message: `Let ${l.imatrikulace} zrušen.` }),
    onError: (e) => notifications.show({ message: e.message, color: 'red' }),
    onSettled: () => {
      void klient.invalidateQueries({ queryKey: PREHLED_KLIC })
      onZavrit()
    },
  })
  return (
    <Modal
      opened={let_ !== null}
      onClose={onZavrit}
      title={let_ ? `Zrušit let ${let_.imatrikulace}` : ''}
      centered
    >
      <Stack>
        <Text fz="sm" c="dimmed">
          Let se nesmaže, jen se označí jako zrušený a nepočítá se do součtů. Vyberte důvod:
        </Text>
        {(c?.duvody_zruseni ?? []).map((d) => (
          <Button
            key={d.hodnota}
            variant="default"
            size="md"
            loading={zruseni.isPending && zruseni.variables === d.hodnota}
            onClick={() => zruseni.mutate(d.hodnota)}
          >
            {d.nazev}
          </Button>
        ))}
      </Stack>
    </Modal>
  )
}
