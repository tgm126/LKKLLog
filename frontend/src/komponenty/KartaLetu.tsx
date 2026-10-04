import { ActionIcon, Badge, Button, Card, Group, Menu, Stack, Text } from '@mantine/core'

import type { Let } from '../api/lety'
import { bezi, doba, hhmm, hhmmss, muzeTg } from '../cas'
import { KATEGORIE_LETU, useNazvy } from '../nazvy'
import { useCiselniky } from '../useLety'
import { varovani } from '../varovani'

export function KartaLetu({
  let_,
  ted,
  konecSoumraku,
  onVzlet,
  onTg,
  onPristani,
  onZrusit,
  onDetail,
  onOpravit,
  onDalsi,
  pracuje,
}: {
  let_: Let
  ted: Date
  konecSoumraku: string
  onVzlet: () => void
  onTg: () => void
  onPristani: () => void
  onZrusit: () => void
  onDetail: () => void
  onOpravit: () => void
  onDalsi: () => void
  pracuje: boolean
}) {
  const { data: c } = useCiselniky()
  const n = useNazvy(c)
  const pozor = varovani(let_, ted, konecSoumraku)
  const menu = let_.muze_ovladat && let_.stav !== 'zrusen'
  const bezici = let_.stav === 've_vzduchu' && let_.cas_vzletu ? bezi(let_.cas_vzletu, ted) : null
  const posadka = let_.posadka
    .map((p) => (p.funkce === 'clen' ? p.jmeno : `${p.jmeno} (${n.funkce(p.funkce)})`))
    .join(', ')

  return (
    <Card
      withBorder
      padding="sm"
      onClick={onDetail}
      style={{ cursor: 'pointer', ...(pozor ? { borderColor: 'var(--mantine-color-red-6)' } : {}) }}
    >
      <Stack gap={6}>
        <Group justify="space-between" wrap="nowrap" align="flex-start">
          <div>
            <Group gap="xs">
              <Text fw={700} fz="lg">
                {let_.imatrikulace}
              </Text>
              <Text c="dimmed" fz="sm">
                {let_.typ}
              </Text>
            </Group>
            <Text fz="sm">
              {KATEGORIE_LETU[let_.kategorie]} · {n.ucel(let_.ucel).toLowerCase()}
              {let_.zpusob_vzletu !== 'vlastni' && ` · ${n.zpusob(let_.zpusob_vzletu).toLowerCase()}`}
            </Text>
          </div>
          <Group gap={4} wrap="nowrap" align="flex-start">
            {bezici && (
              <Text ff="monospace" fw={700} fz="xl" c={pozor ? 'red' : undefined}>
                {bezici}
              </Text>
            )}
            {let_.stav === 'ukoncen' && (
              <Text ff="monospace" fw={700} fz="lg">
                {doba(let_.doba_uctovana_min)}
              </Text>
            )}
            {menu && (
              // Menu nesmí otevírat detail (klik na kartu).
              <div onClick={(e) => e.stopPropagation()}>
                <Menu position="bottom-end">
                  <Menu.Target>
                    <ActionIcon variant="subtle" color="gray" size="lg" aria-label="Další akce">
                      ⋯
                    </ActionIcon>
                  </Menu.Target>
                  <Menu.Dropdown>
                    <Menu.Item onClick={onDetail}>Detail a historie</Menu.Item>
                    <Menu.Item onClick={onOpravit}>Opravit…</Menu.Item>
                    {let_.stav === 'ukoncen' && let_.ucel !== 'vlek' && (
                      <Menu.Item onClick={onDalsi}>Další let odsud…</Menu.Item>
                    )}
                    <Menu.Item color="red" onClick={onZrusit}>
                      Zrušit let…
                    </Menu.Item>
                  </Menu.Dropdown>
                </Menu>
              </div>
            )}
          </Group>
        </Group>
        <Text fz="sm">{posadka}</Text>
        {let_.vlek && (
          <Text fz="sm" c="blue">
            ⇄ {let_.vlek}
          </Text>
        )}
        <Group gap={6}>
          {let_.uloha && <Badge variant="light">úl. {let_.uloha}</Badge>}
          {let_.pocet_hostu > 0 && <Badge variant="light">hosté: {let_.pocet_hostu}</Badge>}
          {let_.cas_vzletu && (
            <Badge variant="outline" color="gray">
              {let_.misto_vzletu} {hhmm(let_.cas_vzletu)}
              {let_.cas_pristani && ` → ${let_.misto_pristani} ${hhmm(let_.cas_pristani)}`}
            </Badge>
          )}
          {let_.stav === 've_vzduchu' && let_.pocet_tg > 0 && (
            <Badge variant="light">
              T&G {let_.pocet_tg}
              {let_.casy_tg.length > 0 &&
                ` · naposledy ${hhmmss(let_.casy_tg[let_.casy_tg.length - 1])}`}
            </Badge>
          )}
          {let_.pocet_pristani > 1 && (
            <Badge variant="light">přistání {let_.pocet_pristani}</Badge>
          )}
          {let_.dodatecne && (
            <Badge variant="light" color="grape">
              zapsáno dodatečně
            </Badge>
          )}
          {let_.opraveno_po_uzaverce && (
            <Badge variant="light" color="orange">
              opraveno po uzávěrce
            </Badge>
          )}
          {let_.kratky_let === 'start_bez_doby' && (
            <Badge variant="light" color="orange">
              start bez doby
            </Badge>
          )}
          {let_.stav === 'zrusen' && (
            <Badge color="gray">zrušen: {n.duvod(let_.duvod_zruseni).toLowerCase()}</Badge>
          )}
        </Group>
        {pozor && (
          <Text c="red" fz="sm" fw={500}>
            {pozor}
          </Text>
        )}
        {let_.muze_ovladat && (let_.stav === 've_vzduchu' || let_.stav === 'pripraven') && (
          // Tlačítko nesmí otevírat detail (klik na kartu).
          <div onClick={(e) => e.stopPropagation()}>
            {let_.stav === 've_vzduchu' ? (
              <Group grow gap="xs">
                {muzeTg(let_.kategorie) && (
                  <Button size="lg" variant="light" loading={pracuje} onClick={onTg}>
                    T&G
                  </Button>
                )}
                <Button size="lg" color="green" onClick={onPristani}>
                  PŘISTÁL
                </Button>
              </Group>
            ) : (
              <Button size="lg" fullWidth loading={pracuje} onClick={onVzlet}>
                VZLET
              </Button>
            )}
          </div>
        )}
      </Stack>
    </Card>
  )
}
