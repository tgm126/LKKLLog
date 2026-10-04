import { Alert, Anchor, Button, Checkbox, PasswordInput, Stack, TextInput } from '@mantine/core'
import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router'

import { prihlasit } from '../api/ucet'
import { KartaUctu } from '../komponenty/KartaUctu'
import { useNastavJa } from '../useJa'

export function Prihlaseni() {
  const [email, setEmail] = useState('')
  const [heslo, setHeslo] = useState('')
  const [zapamatovat, setZapamatovat] = useState(true)
  const nastavJa = useNastavJa()
  const prihlaseni = useMutation({
    mutationFn: () => prihlasit(email, heslo, zapamatovat),
    onSuccess: nastavJa,
  })

  return (
    <KartaUctu nadpis="Přihlášení" popis="Evidence letů aeroklubu">
      <form
        onSubmit={(e) => {
          e.preventDefault()
          prihlaseni.mutate()
        }}
      >
        <Stack gap="md">
          {prihlaseni.isError && <Alert color="red">{prihlaseni.error.message}</Alert>}
          <TextInput
            label="E-mail"
            type="email"
            autoComplete="username"
            required
            size="md"
            value={email}
            onChange={(e) => setEmail(e.currentTarget.value)}
          />
          <PasswordInput
            label="Heslo"
            autoComplete="current-password"
            required
            size="md"
            value={heslo}
            onChange={(e) => setHeslo(e.currentTarget.value)}
          />
          <Checkbox
            label="Zapamatovat si mě na tomto zařízení"
            checked={zapamatovat}
            onChange={(e) => setZapamatovat(e.currentTarget.checked)}
          />
          <Button type="submit" size="md" loading={prihlaseni.isPending}>
            Přihlásit se
          </Button>
          <Anchor component={Link} to="/zapomenute-heslo" fz="sm" ta="center">
            Zapomenuté heslo
          </Anchor>
        </Stack>
      </form>
    </KartaUctu>
  )
}
