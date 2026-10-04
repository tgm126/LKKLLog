import { Button, Group, Stack, Text } from '@mantine/core'

/** Počet bez psaní: velká tlačítka − a +. */
export function Pocitadlo({
  popis,
  hodnota,
  onZmena,
  min = 0,
  max = 99,
}: {
  popis: string
  hodnota: number
  onZmena: (n: number) => void
  min?: number
  max?: number
}) {
  return (
    <Stack gap={4}>
      <Text fz="sm" fw={500}>
        {popis}
      </Text>
      <Group gap="sm" wrap="nowrap">
        <Button
          variant="default"
          size="md"
          w={56}
          disabled={hodnota <= min}
          onClick={() => onZmena(hodnota - 1)}
          aria-label={`${popis}: méně`}
        >
          −
        </Button>
        <Text fz={26} fw={700} miw={40} ta="center">
          {hodnota}
        </Text>
        <Button
          variant="default"
          size="md"
          w={56}
          disabled={hodnota >= max}
          onClick={() => onZmena(hodnota + 1)}
          aria-label={`${popis}: více`}
        >
          +
        </Button>
      </Group>
    </Stack>
  )
}
