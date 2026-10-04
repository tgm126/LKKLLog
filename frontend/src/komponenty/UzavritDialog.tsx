import { Alert, Button, Loader, Modal, Stack, Text } from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { nactiNahled, type TypUzaverky, uzavrit } from '../api/uzaverky'
import { datumCesky, nazevObdobi } from '../cas'
import { jeLetovyDotaz } from '../useLety'
import { SouhrnUzaverky } from './SouhrnUzaverky'

/** Uzavření dne nebo měsíce: nejdřív ukáže souhrn a co případně brání uzavření. */
export function UzavritDialog({
  typ,
  obdobi,
  onZavrit,
}: {
  typ: TypUzaverky
  obdobi: string
  onZavrit: () => void
}) {
  const klient = useQueryClient()
  const nahled = useQuery({
    queryKey: ['uzaverky', 'nahled', typ, obdobi],
    queryFn: () => nactiNahled(typ, obdobi),
  })
  const ulozit = useMutation({
    mutationFn: () => uzavrit(typ, obdobi),
    onSuccess: (u) => {
      notifications.show({
        message: `${typ === 'den' ? 'Den' : 'Měsíc'} uzavřen${u.verze > 1 ? ` (verze ${u.verze})` : ''}.`,
        color: 'green',
      })
      onZavrit()
    },
    onError: (e) => notifications.show({ message: e.message, color: 'red' }),
    onSettled: () => klient.invalidateQueries({ predicate: jeLetovyDotaz }),
  })
  const n = nahled.data
  const prepocet = n?.posledni?.platna
  const akce = prepocet ? 'Přepočítat' : typ === 'den' ? 'Uzavřít den' : 'Uzavřít měsíc'

  return (
    <Modal opened onClose={onZavrit} title={`${akce}: ${nazevObdobi(typ, obdobi)}`} size="lg">
      {nahled.isPending && <Loader />}
      {nahled.isError && <Alert color="red">{nahled.error.message}</Alert>}
      {n && (
        <Stack>
          {n.zakaz && <Alert color="gray">{n.zakaz}</Alert>}
          {n.neukonceno.length > 0 && (
            <Alert color="orange" title="Nejdřív ukončete nebo zrušte lety">
              {n.neukonceno.join(', ')}
            </Alert>
          )}
          {n.neuzavrene_dny.length > 0 && (
            <Alert color="orange" title="Nejdřív uzavřete dny">
              {n.neuzavrene_dny.map((d) => datumCesky(d)).join(', ')}
            </Alert>
          )}
          {n.dnes && !prepocet && (
            <Text fz="sm" c="orange">
              Uzavíráte dnešek – piloti pak už dnes nemohou zakládat ani opravovat lety, zapíše je
              jen časoměřič.
            </Text>
          )}
          {prepocet && (
            <Text fz="sm" c="dimmed">
              Uloží se nová verze souhrnu ({n.posledni!.verze + 1}); předchozí zůstanou v historii.
            </Text>
          )}
          <SouhrnUzaverky souhrn={n.souhrn} />
          <Button size="lg" disabled={!n.lze} loading={ulozit.isPending} onClick={() => ulozit.mutate()}>
            {akce}
          </Button>
        </Stack>
      )}
    </Modal>
  )
}
