import { Alert, Anchor, Button, Loader, PasswordInput, Stack, Text } from '@mantine/core'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'

import { nastavitHeslo, overitOdkaz } from '../api/ucet'
import { KartaUctu } from '../komponenty/KartaUctu'
import { useNastavJa } from '../useJa'

export function NastavitHeslo() {
  const { uid = '', token = '' } = useParams()
  const [heslo, setHeslo] = useState('')
  const [kontrola, setKontrola] = useState('')
  const nastavJa = useNastavJa()
  const navigovat = useNavigate()
  const odkaz = useQuery({
    queryKey: ['odkaz', uid, token],
    queryFn: () => overitOdkaz(uid, token),
    retry: false,
  })
  const ulozeni = useMutation({
    mutationFn: () => nastavitHeslo(uid, token, heslo),
    onSuccess: (ja) => {
      nastavJa(ja)
      navigovat('/', { replace: true })
    },
  })
  const neshoda = kontrola.length > 0 && heslo !== kontrola

  return (
    <KartaUctu nadpis="Nastavení hesla">
      {odkaz.isPending && <Loader />}
      {odkaz.isError && (
        <>
          <Alert color="red">{odkaz.error.message}</Alert>
          <Anchor component={Link} to="/zapomenute-heslo" fz="sm">
            Požádat o nový odkaz
          </Anchor>
        </>
      )}
      {odkaz.isSuccess && (
        <form
          onSubmit={(e) => {
            e.preventDefault()
            if (!neshoda) ulozeni.mutate()
          }}
        >
          <Stack gap="md">
            <Text fz="sm">
              Účet: <b>{odkaz.data.zprava}</b>
            </Text>
            {ulozeni.isError && <Alert color="red">{ulozeni.error.message}</Alert>}
            <PasswordInput
              label="Nové heslo"
              description="Alespoň 8 znaků, ne jen čísla a ne příliš běžné."
              autoComplete="new-password"
              required
              size="md"
              value={heslo}
              onChange={(e) => setHeslo(e.currentTarget.value)}
            />
            <PasswordInput
              label="Heslo znovu"
              autoComplete="new-password"
              required
              size="md"
              value={kontrola}
              error={neshoda ? 'Hesla se neshodují.' : undefined}
              onChange={(e) => setKontrola(e.currentTarget.value)}
            />
            <Button type="submit" size="md" loading={ulozeni.isPending} disabled={neshoda}>
              Uložit heslo a přihlásit se
            </Button>
          </Stack>
        </form>
      )}
    </KartaUctu>
  )
}
