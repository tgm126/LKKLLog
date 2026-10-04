import { Alert, Button, Group, List, Loader, Modal, Stack, Text } from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  jeIos,
  jeNaPlose,
  nactiStavPush,
  odberZarizeni,
  pushPodporovan,
  vypnoutPush,
  zapnoutPush,
  zkusebniPush,
} from '../api/push'

/** Zapnutí push upozornění na neukončené lety na tomto zařízení. */
export function UpozorneniDialog({ onZavrit }: { onZavrit: () => void }) {
  const klient = useQueryClient()
  const podporovan = pushPodporovan()
  const stav = useQuery({ queryKey: ['push'], queryFn: nactiStavPush })
  const zarizeni = useQuery({
    queryKey: ['push', 'zarizeni'],
    queryFn: async () => (await odberZarizeni()) !== null,
    enabled: podporovan,
  })
  const obnovit = () => klient.invalidateQueries({ queryKey: ['push'] })
  const chyba = (e: Error) => notifications.show({ message: e.message, color: 'red' })

  const zapnout = useMutation({
    mutationFn: () => zapnoutPush(stav.data!.klic),
    onSuccess: () => notifications.show({ message: 'Upozornění zapnuta.', color: 'green' }),
    onError: chyba,
    onSettled: obnovit,
  })
  const vypnout = useMutation({ mutationFn: vypnoutPush, onError: chyba, onSettled: obnovit })
  const zkouska = useMutation({
    mutationFn: zkusebniPush,
    onSuccess: (o) =>
      notifications.show({
        message: o.pocet ? `Odesláno na ${o.pocet} zařízení.` : 'Žádné zařízení nepřijalo.',
      }),
    onError: chyba,
  })

  const ios = jeIos() && !jeNaPlose()
  return (
    <Modal opened onClose={onZavrit} title="Upozornění na neukončené lety" centered>
      <Stack>
        <Text fz="sm">
          Upozornění přijde k letům, které jste založili nebo na kterých jste PIC, žák či
          přezkoušený, když let:
        </Text>
        <List fz="sm" spacing={2}>
          <List.Item>je ve vzduchu déle než maximální doba letadla,</List.Item>
          <List.Item>je ve vzduchu ještě po konci soumraku,</List.Item>
          <List.Item>zůstal neukončený z minulého dne (den pak nejde uzavřít).</List.Item>
        </List>
        <Text fz="sm" c="dimmed">
          Stejné upozornění chodí i e-mailem. Upozornění se posílají jen přes den (6–22 h).
        </Text>

        {!podporovan || ios ? (
          <Alert color="orange">
            {ios
              ? 'Na iPhonu a iPadu fungují upozornění jen v aplikaci přidané na plochu: v Safari ťukněte na Sdílet → Přidat na plochu a otevřete LKKL Log z plochy.'
              : 'Tento prohlížeč push upozornění neumí.'}
          </Alert>
        ) : zarizeni.isPending || stav.isPending ? (
          <Loader size="sm" />
        ) : zarizeni.data ? (
          <>
            <Alert color="green">Na tomto zařízení jsou upozornění zapnutá.</Alert>
            <Group grow>
              <Button variant="default" loading={zkouska.isPending} onClick={() => zkouska.mutate()}>
                Poslat zkušební
              </Button>
              <Button variant="default" color="red" loading={vypnout.isPending} onClick={() => vypnout.mutate()}>
                Vypnout
              </Button>
            </Group>
          </>
        ) : (
          <Button size="md" loading={zapnout.isPending} onClick={() => zapnout.mutate()}>
            Zapnout upozornění na tomto zařízení
          </Button>
        )}
        {stav.data && stav.data.zarizeni > 0 && (
          <Text fz="xs" c="dimmed">
            Upozornění máte zapnutá na {stav.data.zarizeni}{' '}
            {stav.data.zarizeni === 1 ? 'zařízení' : 'zařízeních'}.
          </Text>
        )}
      </Stack>
    </Modal>
  )
}
