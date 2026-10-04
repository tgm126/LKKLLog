import { Alert, Anchor, Button, Stack, TextInput } from '@mantine/core'
import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router'

import { zapomenuteHeslo } from '../api/ucet'
import { KartaUctu } from '../komponenty/KartaUctu'

export function ZapomenuteHeslo() {
  const [email, setEmail] = useState('')
  const zadost = useMutation({ mutationFn: () => zapomenuteHeslo(email) })

  return (
    <KartaUctu
      nadpis="Zapomenuté heslo"
      popis="Pošleme vám e-mail s odkazem, přes který si nastavíte nové heslo."
    >
      {zadost.isSuccess ? (
        <Alert color="green">{zadost.data.zprava}</Alert>
      ) : (
        <form
          onSubmit={(e) => {
            e.preventDefault()
            zadost.mutate()
          }}
        >
          <Stack gap="md">
            {zadost.isError && <Alert color="red">{zadost.error.message}</Alert>}
            <TextInput
              label="E-mail"
              type="email"
              autoComplete="username"
              required
              size="md"
              value={email}
              onChange={(e) => setEmail(e.currentTarget.value)}
            />
            <Button type="submit" size="md" loading={zadost.isPending}>
              Poslat odkaz
            </Button>
          </Stack>
        </form>
      )}
      <Anchor component={Link} to="/" fz="sm" ta="center">
        Zpět na přihlášení
      </Anchor>
    </KartaUctu>
  )
}
