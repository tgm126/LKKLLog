import {
  Alert,
  Button,
  Checkbox,
  Group,
  Loader,
  Modal,
  MultiSelect,
  NumberInput,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
} from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import {
  type Ciselnik,
  nactiCiselnik,
  type PoleCiselniku,
  type RadekCiselniku,
  smazatPolozku,
  ulozitPolozku,
} from '../api/ciselniky'

/** Text buňky: ano/ne jako ✓, volby jako názvy. */
function bunka(pole: PoleCiselniku, hodnota: unknown): string {
  const nazev = (v: unknown) => pole.volby.find(([h]) => h === v)?.[1] ?? String(v ?? '')
  if (pole.typ === 'bool') return hodnota ? '✓' : ''
  if (pole.typ === 'vice') return ((hodnota as unknown[]) ?? []).map(nazev).join(', ')
  if (pole.typ === 'volba') return nazev(hodnota)
  return String(hodnota ?? '')
}

function PolozkaDialog({
  ciselnik,
  radek,
  rodic,
  onZavrit,
}: {
  ciselnik: Ciselnik
  radek: RadekCiselniku | null
  rodic: number | null
  onZavrit: () => void
}) {
  const klient = useQueryClient()
  const [hodnoty, setHodnoty] = useState<Record<string, unknown>>(
    () =>
      radek?.hodnoty ??
      Object.fromEntries(
        ciselnik.pole.map((p) => [p.klic, p.typ === 'bool' ? p.klic === 'aktivni' : p.typ === 'vice' ? [] : p.klic === 'poradi' ? 100 : ''])
      ),
  )
  const hotovo = (data: Ciselnik) => {
    klient.setQueryData(['ciselnik', ciselnik.klic, rodic], data)
    void klient.invalidateQueries({ queryKey: ['sprava-ciselniky'] })
    void klient.invalidateQueries({ queryKey: ['ciselniky'] }) // letiště, úlohy v průvodci
    onZavrit()
  }
  const chyba = (e: Error) => notifications.show({ message: e.message, color: 'red' })
  const ulozeni = useMutation({
    mutationFn: () => ulozitPolozku(ciselnik.klic, { id: radek?.id, rodic, hodnoty }),
    onSuccess: hotovo,
    onError: chyba,
  })
  const smazani = useMutation({ mutationFn: () => smazatPolozku(ciselnik.klic, radek!.id), onSuccess: hotovo, onError: chyba })
  const nastav = (klic: string, v: unknown) => setHodnoty({ ...hodnoty, [klic]: v })

  return (
    <Modal opened onClose={onZavrit} title={radek ? 'Upravit položku' : 'Nová položka'} size="md">
      <Stack gap="xs">
        {radek?.systemova && (
          <Text fz="xs" c="dimmed">
            Systémová hodnota – počítají s ní pravidla aplikace. Lze ji přejmenovat a deaktivovat.
          </Text>
        )}
        {ciselnik.pole.map((p) => {
          const v = hodnoty[p.klic]
          const data = p.volby.map(([value, label]) => ({ value, label }))
          if (p.typ === 'bool')
            return <Checkbox key={p.klic} label={p.nazev} checked={!!v} onChange={(e) => nastav(p.klic, e.currentTarget.checked)} />
          if (p.typ === 'cislo')
            return <NumberInput key={p.klic} label={p.nazev} min={0} value={Number(v ?? 0)} onChange={(n) => nastav(p.klic, n)} />
          if (p.typ === 'volba')
            return <Select key={p.klic} label={p.nazev} data={data} value={(v as string) || null} onChange={(n) => nastav(p.klic, n)} allowDeselect={false} />
          if (p.typ === 'vice')
            return <MultiSelect key={p.klic} label={p.nazev} data={data} value={(v as string[]) ?? []} onChange={(n) => nastav(p.klic, n)} />
          return <TextInput key={p.klic} label={p.nazev} value={String(v ?? '')} onChange={(e) => nastav(p.klic, e.currentTarget.value)} />
        })}
        <Group justify="space-between" mt="xs">
          {radek && !radek.systemova ? (
            <Button variant="subtle" color="red" size="compact-sm" loading={smazani.isPending} onClick={() => smazani.mutate()}>
              Smazat
            </Button>
          ) : (
            <span />
          )}
          <Button size="compact-sm" loading={ulozeni.isPending} onClick={() => ulozeni.mutate()}>
            Uložit
          </Button>
        </Group>
      </Stack>
    </Modal>
  )
}

/** Hustá tabulka položek číselníku; řádek otevře úpravu, u hierarchie i podřízené položky. */
export function TabulkaCiselniku({
  klic,
  rodic = null,
  nadpis,
  vybrany,
  onVyber,
}: {
  klic: string
  rodic?: number | null
  nadpis?: string
  vybrany?: number | null
  onVyber?: (radek: RadekCiselniku) => void
}) {
  const dotaz = useQuery({ queryKey: ['ciselnik', klic, rodic], queryFn: () => nactiCiselnik(klic, rodic) })
  const [uprava, setUprava] = useState<RadekCiselniku | null | undefined>(undefined)
  const c = dotaz.data
  if (dotaz.isPending) return <Loader size="sm" />
  if (dotaz.isError) return <Alert color="red">{dotaz.error.message}</Alert>
  if (!c) return null
  // Pořadí je technický údaj – v tabulce zbytečně zabírá místo, upravuje se v dialogu.
  const sloupce = c.pole.filter((p) => p.klic !== 'poradi')

  return (
    <Stack gap={6}>
      <Group justify="space-between" wrap="nowrap">
        <div>
          <Text fw={600}>{nadpis ?? c.nazev}</Text>
          {c.popis && !nadpis && (
            <Text fz="xs" c="dimmed">
              {c.popis}
            </Text>
          )}
        </div>
        <Button size="compact-sm" variant="light" onClick={() => setUprava(null)}>
          + Přidat
        </Button>
      </Group>
      <Table.ScrollContainer minWidth={420}>
        <Table fz="sm" verticalSpacing={4} horizontalSpacing="sm" highlightOnHover withTableBorder>
          <Table.Thead>
            <Table.Tr>
              {sloupce.map((p) => (
                <Table.Th key={p.klic} fz="xs" c="dimmed" fw={500}>
                  {p.nazev}
                </Table.Th>
              ))}
              <Table.Th />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {c.radky.map((r) => (
              <Table.Tr
                key={r.id}
                onClick={() => (onVyber ? onVyber(r) : setUprava(r))}
                bg={vybrany === r.id ? 'var(--mantine-color-blue-light)' : undefined}
                c={r.hodnoty.aktivni === false ? 'dimmed' : undefined}
                style={{ cursor: 'pointer' }}
              >
                {sloupce.map((p) => (
                  <Table.Td key={p.klic}>{bunka(p, r.hodnoty[p.klic])}</Table.Td>
                ))}
                <Table.Td style={{ whiteSpace: 'nowrap', width: '1%' }}>
                  <Group gap={8} wrap="nowrap" justify="flex-end">
                    {r.systemova && (
                      <Text span fz="xs" c="dimmed">
                        systémová
                      </Text>
                    )}
                    {onVyber && (
                      <Button
                        size="compact-xs"
                        variant="subtle"
                        onClick={(e) => {
                          e.stopPropagation()
                          setUprava(r)
                        }}
                      >
                        upravit
                      </Button>
                    )}
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
            {c.radky.length === 0 && (
              <Table.Tr>
                <Table.Td colSpan={sloupce.length + 1} c="dimmed">
                  Zatím prázdné.
                </Table.Td>
              </Table.Tr>
            )}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>
      {uprava !== undefined && (
        <PolozkaDialog ciselnik={c} radek={uprava} rodic={rodic} onZavrit={() => setUprava(undefined)} />
      )}
    </Stack>
  )
}
