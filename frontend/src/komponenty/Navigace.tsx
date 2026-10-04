import { Button, Group } from '@mantine/core'
import { NavLink } from 'react-router'

/** Přepínání hlavních obrazovek pod záhlavím. */
export function Navigace() {
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
    </Group>
  )
}
