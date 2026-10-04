import { Badge, Card, Container, Group, Stack, Text, Title } from '@mantine/core'

import { useJa } from '../useJa'

/** Dočasná úvodní stránka po přihlášení – přehled dne přijde v etapě 3. */
export function Uvod() {
  const { data: ja } = useJa()
  if (!ja?.prihlasen) return null
  return (
    <Container size="sm" py="lg">
      <Stack gap="md">
        <Title order={2}>Vítejte, {ja.jmeno}</Title>
        <Card withBorder padding="lg">
          <Stack gap="xs">
            <Text>
              Jste přihlášen jako {ja.jmeno} {ja.prijmeni} ({ja.email}).
            </Text>
            <Group gap={4}>
              <Text fz="sm" c="dimmed">
                Role:
              </Text>
              <Badge variant="light">pilot</Badge>
              {ja.role?.casomeric && <Badge variant="light">časoměřič / věž</Badge>}
              {ja.role?.ucetni && <Badge variant="light">účetní</Badge>}
              {ja.role?.admin && (
                <Badge variant="light" color="red">
                  admin
                </Badge>
              )}
            </Group>
            <Text c="dimmed" fz="sm">
              Přehled dne a zápis letů přibudou v další etapě.
            </Text>
          </Stack>
        </Card>
      </Stack>
    </Container>
  )
}
