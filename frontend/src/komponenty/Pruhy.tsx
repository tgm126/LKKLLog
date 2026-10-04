import { Button, Group, Paper, Text } from '@mantine/core'
import { useMutation } from '@tanstack/react-query'

import { vratitSe } from '../api/ucet'
import { useJa } from '../useJa'

/** Výrazné pruhy nahoře: testovací provoz a „přihlášen jako“. */
export function Pruhy() {
  const { data: ja } = useJa()
  const navrat = useMutation({
    mutationFn: vratitSe,
    // Admin se vrací do administrace, odkud se přepnul.
    onSuccess: () => window.location.assign('/admin/osoby/osoba/'),
  })
  if (!ja) return null
  return (
    <>
      {ja.testovaci_provoz && (
        <Paper radius={0} py={4} bg="yellow.5" c="dark.9" ta="center">
          <Text fw={700} fz="sm">
            TESTOVACÍ PROVOZ – data nejsou skutečná
          </Text>
        </Paper>
      )}
      {ja.zastupce && (
        <Paper radius={0} py={6} px="md" bg="red.7" c="white">
          <Group justify="center" gap="sm">
            <Text fw={700} fz="sm">
              Jste přihlášen jako {ja.jmeno} {ja.prijmeni}
            </Text>
            <Button
              size="xs"
              variant="white"
              color="red"
              loading={navrat.isPending}
              onClick={() => navrat.mutate()}
            >
              Vrátit se ({ja.zastupce.jmeno})
            </Button>
          </Group>
        </Paper>
      )}
    </>
  )
}
