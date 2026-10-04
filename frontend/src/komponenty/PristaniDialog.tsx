import { Alert, Button, Group, Modal, Select, Stack, Text } from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { ApiChyba } from '../api/klient'
import { type Let, pristat, zrusitLet } from '../api/lety'
import { hhmmss, muzeTg } from '../cas'
import { jeLetovyDotaz, useCiselniky } from '../useLety'
import { oznamitSeZpet } from '../zpet'
import { Pocitadlo } from './Pocitadlo'

/** Potvrzení přistání: místo, počet touch-and-go a u letu do 1 minuty volba, jak ho brát. */
export function PristaniDialog({ let_, onZavrit }: { let_: Let | null; onZavrit: () => void }) {
  const { data: c } = useCiselniky()
  const klient = useQueryClient()
  const domovske = c?.letiste.find((l) => l.domovske)
  const [misto, setMisto] = useState<string | null>(null)
  // Dokud se počet neupraví, platí T&G zapsané během letu.
  const [upravenyTg, setTg] = useState<number | null>(null)
  const tg = upravenyTg ?? let_?.pocet_tg ?? 0
  const [kratky, setKratky] = useState(false)

  const zavrit = () => {
    setMisto(null)
    setTg(null)
    setKratky(false)
    onZavrit()
  }
  const hotovo = (zprava: string, l?: Let) => {
    if (l) oznamitSeZpet(l, zprava, klient)
    else notifications.show({ message: zprava, color: 'green' })
    void klient.invalidateQueries({ predicate: jeLetovyDotaz })
    zavrit()
  }
  const chyba = (e: Error) => {
    if (e instanceof ApiChyba && e.kod === 'kratky_let') {
      setKratky(true)
      return
    }
    notifications.show({ message: e.message, color: 'red' })
    void klient.invalidateQueries({ predicate: jeLetovyDotaz })
    zavrit()
  }
  const ulozit = useMutation({
    mutationFn: (kratkyLet: string) =>
      pristat(let_!.id, {
        misto_pristani_id: misto ? Number(misto) : (domovske?.id ?? null),
        pocet_tg: tg,
        kratky_let: kratkyLet,
      }),
    onSuccess: (l) => hotovo(`${l.imatrikulace} přistál.`, l),
    onError: chyba,
  })
  const nepocitat = useMutation({
    mutationFn: () => zrusitLet(let_!.id, 'preruseny_vzlet'),
    onSuccess: (l) => hotovo(`${l.imatrikulace}: přerušený vzlet, let se nepočítá.`),
    onError: chyba,
  })

  return (
    <Modal
      opened={let_ !== null}
      onClose={zavrit}
      title={let_ ? `Přistání ${let_.imatrikulace}` : ''}
      centered
    >
      {kratky ? (
        <Stack>
          <Alert color="orange">Let trval méně než minutu. Jak ho brát?</Alert>
          <Button size="md" onClick={() => ulozit.mutate('start_bez_doby')}>
            Start se počítá, doba 0 min
          </Button>
          <Button size="md" variant="default" onClick={() => nepocitat.mutate()}>
            Nepočítat (přerušený vzlet)
          </Button>
          <Button size="md" variant="default" onClick={() => ulozit.mutate('normalni')}>
            Normální let (skutečný čas)
          </Button>
        </Stack>
      ) : (
        <Stack>
          <Select
            label="Místo přistání"
            size="md"
            data={(c?.letiste ?? []).map((l) => ({
              value: String(l.id),
              label: l.icao ? `${l.icao} ${l.nazev}` : l.nazev,
            }))}
            value={misto ?? (domovske ? String(domovske.id) : null)}
            onChange={setMisto}
            allowDeselect={false}
          />
          {let_ && muzeTg(let_.kategorie) && (
            <Pocitadlo
              popis="Touch-and-go"
              popisek={
                let_.casy_tg.length > 0
                  ? `Zapsáno během letu: ${let_.casy_tg.map(hhmmss).join(', ')}`
                  : `Přistání celkem: ${tg + 1}`
              }
              hodnota={tg}
              onZmena={setTg}
            />
          )}
          <Text fz="sm" c="dimmed">
            Čas přistání se zapíše podle hodin serveru v okamžiku potvrzení.
          </Text>
          <Group grow>
            <Button variant="default" size="md" onClick={zavrit}>
              Zpět
            </Button>
            <Button size="md" color="green" loading={ulozit.isPending} onClick={() => ulozit.mutate('')}>
              Potvrdit přistání
            </Button>
          </Group>
        </Stack>
      )}
    </Modal>
  )
}
