import { Anchor, Badge, Button, Group, Menu, Text, Title } from '@mantine/core'
import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router'

import { odhlasit } from '../api/ucet'
import { useJa, useNastavJa } from '../useJa'
import { HodinyUtc } from './HodinyUtc'
import { UpozorneniDialog } from './UpozorneniDialog'

export function Zahlavi() {
  const { data: ja } = useJa()
  const nastavJa = useNastavJa()
  const odhlaseni = useMutation({ mutationFn: odhlasit, onSuccess: nastavJa })
  const [upozorneni, setUpozorneni] = useState(false)

  return (
    <Group justify="space-between" px="md" py="sm" wrap="nowrap">
      <Title order={3}>LKKL Log</Title>
      <Group gap="md" wrap="nowrap">
        <HodinyUtc />
        {ja?.prihlasen && (
          <Menu position="bottom-end" withinPortal>
            <Menu.Target>
              <Button variant="default" size="sm">
                {ja.jmeno}
              </Button>
            </Menu.Target>
            <Menu.Dropdown>
              <Menu.Label>
                {ja.jmeno} {ja.prijmeni}
              </Menu.Label>
              <Group gap={4} px="xs" pb="xs">
                <Badge variant="light">pilot</Badge>
                {ja.role?.casomeric && <Badge variant="light">časoměřič / věž</Badge>}
                {ja.role?.ucetni && <Badge variant="light">účetní</Badge>}
                {ja.role?.spravce && <Badge variant="light">správce licencí a letadel</Badge>}
                {ja.role?.admin && <Badge variant="light" color="red">admin</Badge>}
              </Group>
              {ja.role?.admin && !ja.zastupce && (
                <Menu.Item component="a" href="/admin/">
                  Technická administrace
                </Menu.Item>
              )}
              {(ja.role?.admin || ja.role?.spravce) && (
                <Menu.Item component={Link} to={`/osoby/${ja.id}`}>
                  Moje karta
                </Menu.Item>
              )}
              {!ja.zastupce && (
                <Menu.Item onClick={() => setUpozorneni(true)}>Upozornění na telefon…</Menu.Item>
              )}
              <Menu.Item onClick={() => odhlaseni.mutate()}>Odhlásit se</Menu.Item>
            </Menu.Dropdown>
          </Menu>
        )}
        {upozorneni && <UpozorneniDialog onZavrit={() => setUpozorneni(false)} />}
      </Group>
    </Group>
  )
}

export function Paticka({ verze }: { verze?: string }) {
  return (
    <Text c="dimmed" fz="xs" ta="center" py="md">
      LKKL Log {verze ? `· verze ${verze}` : ''} ·{' '}
      <Anchor href="mailto:info@lkkl.cz" fz="xs">
        info@lkkl.cz
      </Anchor>
    </Text>
  )
}
