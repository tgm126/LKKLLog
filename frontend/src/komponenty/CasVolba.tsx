import { ActionIcon, Button, Group, Stack, Text } from '@mantine/core'

/** Výběr času bez psaní: tlačítka ±1/±10 minut a „teď“. Zobrazuje se v UTC. */
export function CasVolba({
  popis,
  hodnota,
  onZmena,
  ted,
}: {
  popis: string
  hodnota: Date
  onZmena: (d: Date) => void
  ted: Date
}) {
  const posun = (minut: number) => onZmena(new Date(hodnota.getTime() + minut * 60_000))
  const jinyDen = hodnota.toISOString().slice(0, 10) !== ted.toISOString().slice(0, 10)
  return (
    <Stack gap={4}>
      <Text fz="sm" fw={500}>
        {popis}
      </Text>
      <Group gap="xs" wrap="nowrap">
        <Button variant="default" size="md" px="xs" onClick={() => posun(-10)}>
          −10
        </Button>
        <Button variant="default" size="md" px="xs" onClick={() => posun(-1)}>
          −1
        </Button>
        <Stack gap={0} align="center" miw={92}>
          <Text ff="monospace" fz={26} fw={700} lh={1.1}>
            {hodnota.toISOString().slice(11, 16)}
          </Text>
          <Text fz="xs" c={jinyDen ? 'orange' : 'dimmed'}>
            {jinyDen
              ? hodnota.toLocaleDateString('cs-CZ', { timeZone: 'UTC' })
              : 'UTC dnes'}
          </Text>
        </Stack>
        <Button variant="default" size="md" px="xs" onClick={() => posun(1)}>
          +1
        </Button>
        <Button variant="default" size="md" px="xs" onClick={() => posun(10)}>
          +10
        </Button>
      </Group>
      <Group gap="xs">
        <Button variant="subtle" size="xs" onClick={() => onZmena(new Date(ted))}>
          teď
        </Button>
        <ActionIcon.Group>
          <Button variant="subtle" size="xs" onClick={() => posun(-60)}>
            −1 h
          </Button>
          <Button variant="subtle" size="xs" onClick={() => posun(60)}>
            +1 h
          </Button>
          <Button variant="subtle" size="xs" onClick={() => posun(-24 * 60)}>
            −1 den
          </Button>
        </ActionIcon.Group>
      </Group>
    </Stack>
  )
}
