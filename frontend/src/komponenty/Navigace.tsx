import { Button, Group } from '@mantine/core'
import { NavLink } from 'react-router'

import { useJa } from '../useJa'

/** Přepínání hlavních obrazovek pod záhlavím. */
export function Navigace() {
  const { data: ja } = useJa()
  const role = ja?.role
  const odkaz = (cesta: string, text: string) => (
    <NavLink to={cesta} end style={{ textDecoration: 'none' }}>
      {({ isActive }) => (
        <Button size="sm" variant={isActive ? 'light' : 'subtle'} color={isActive ? 'blue' : 'gray'}>
          {text}
        </Button>
      )}
    </NavLink>
  )
  return (
    <Group gap={4} px="md" pb="xs">
      {odkaz('/', 'Dnes')}
      {odkaz('/vypis', 'Výpis')}
      {(role?.casomeric || role?.ucetni || role?.admin) && odkaz('/uzaverky', 'Uzávěrky')}
    </Group>
  )
}
