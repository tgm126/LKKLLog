import {
  Alert,
  Button,
  Group,
  Modal,
  SegmentedControl,
  Select,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
} from '@mantine/core'
import { useMediaQuery } from '@mantine/hooks'
import { notifications } from '@mantine/notifications'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { ApiChyba } from '../api/klient'
import { type Let, type Oprava, opravitLet } from '../api/lety'
import { jmeno, nabidka, SLOTY, UCELY } from '../posadka'
import { jeLetovyDotaz, useCiselniky } from '../useLety'
import { CasVolba } from './CasVolba'
import { DalsiClenove } from './DalsiClenove'
import { Pocitadlo } from './Pocitadlo'

/** Oprava letu: stejná pole jako při zakládání + povinný důvod. Otevírá se s klíčem
 * podle verze letu, takže pole vždy začínají z aktuálního stavu. */
export function OpravaLetu({
  let_,
  onZavrit,
  ted,
  lety,
}: {
  let_: Let
  onZavrit: () => void
  ted: Date
  lety: Let[]
}) {
  const { data: c } = useCiselniky()
  const mobil = useMediaQuery('(max-width: 48em)')
  const hledani = useMediaQuery('(pointer: fine)') ?? true
  const klient = useQueryClient()

  const clen = (funkce: string) => let_.posadka.find((p) => p.funkce === funkce)?.osoba_id
  const druhyPuvodni = let_.posadka.find((p) => p.funkce !== 'pic' && p.funkce !== 'clen')

  const [letadloId, setLetadloId] = useState(String(let_.letadlo_id))
  const [ucel, setUcel] = useState(let_.ucel)
  const [pic, setPic] = useState<string | null>(clen('pic') ? String(clen('pic')) : null)
  const [druhy, setDruhy] = useState<string | null>(
    druhyPuvodni ? String(druhyPuvodni.osoba_id) : null,
  )
  const [clenove, setClenove] = useState<string[]>(
    let_.posadka.filter((p) => p.funkce === 'clen').map((p) => String(p.osoba_id)),
  )
  const [hoste, setHoste] = useState(let_.pocet_hostu)
  const [platce, setPlatce] = useState<string | null>(
    let_.plati_aeroklub ? 'aeroklub' : let_.platce_id ? String(let_.platce_id) : null,
  )
  const [ulohaId, setUlohaId] = useState<string | null>(let_.uloha_id ? String(let_.uloha_id) : null)
  const [zpusob, setZpusob] = useState(let_.zpusob_vzletu)
  const [mistoVzletu, setMistoVzletu] = useState(String(let_.misto_vzletu_id))
  const [casVzletu, setCasVzletu] = useState(() => new Date(let_.cas_vzletu ?? ted))
  const [casPristani, setCasPristani] = useState(() => new Date(let_.cas_pristani ?? ted))
  const [mistoPristani, setMistoPristani] = useState(
    let_.misto_pristani_id ? String(let_.misto_pristani_id) : null,
  )
  const [tg, setTg] = useState(let_.pocet_tg)
  const [kratky, setKratky] = useState(let_.kratky_let || 'start_bez_doby')
  const [duvod, setDuvod] = useState<string | null>(null)
  const [poznamka, setPoznamka] = useState('')

  const letadlo = c?.letadla.find((l) => String(l.id) === letadloId)
  const sloty = SLOTY[ucel] ?? SLOTY.normalni
  const tah = let_.ucel === 'vlek'
  const ukonceny = let_.stav === 'ukoncen'
  const maVzlet = let_.stav !== 'pripraven'
  const veVzduchu = new Set(
    lety
      .filter((l) => l.stav === 've_vzduchu' && l.id !== let_.id)
      .flatMap((l) => l.posadka.filter((p) => p.funkce !== 'dozor').map((p) => p.osoba_id)),
  )

  const posadka = [
    ...(pic ? [{ osoba_id: Number(pic), funkce: 'pic' }] : []),
    ...(druhy && sloty.druhy ? [{ osoba_id: Number(druhy), funkce: sloty.druhy.funkce }] : []),
    ...(ucel === 'normalni' && !tah
      ? clenove.map((id) => ({ osoba_id: Number(id), funkce: 'clen' }))
      : []),
  ]
  const moznostiPlatce = (c?.osoby ?? [])
    .filter((o) => posadka.some((p) => p.osoba_id === o.id && p.funkce !== 'dozor') && !o.externi)
    .map((o) => ({ value: String(o.id), label: jmeno(o) }))
  const ulohy = (c?.osnovy ?? [])
    .filter((o) => o.kategorie === letadlo?.kategorie)
    .map((o) => ({
      group: o.nazev,
      items: o.ulohy
        .filter((u) => u.ucely.includes(ucel))
        .map((u) => ({ value: String(u.id), label: `${u.kod} – ${u.nazev}` })),
    }))
    .filter((g) => g.items.length > 0)
  const letiste = (c?.letiste ?? []).map((l) => ({
    value: String(l.id),
    label: l.icao ? `${l.icao} ${l.nazev}` : l.nazev,
  }))
  const kratkyLet = ukonceny && casPristani.getTime() - casVzletu.getTime() < 60_000
  const platceOk = platce === 'aeroklub' || moznostiPlatce.some((m) => m.value === platce)

  const ulozeni = useMutation({
    mutationFn: () => {
      const data: Oprava = {
        letadlo_id: Number(letadloId),
        ucel,
        posadka,
        uloha_id: ulohaId ? Number(ulohaId) : null,
        zpusob_vzletu: letadlo?.kategorie === 'kluzak' ? zpusob : 'vlastni',
        misto_vzletu_id: Number(mistoVzletu),
        pocet_hostu: ucel === 'normalni' ? hoste : 0,
        platce_id: platce && platce !== 'aeroklub' && platceOk ? Number(platce) : null,
        plati_aeroklub: platce === 'aeroklub',
        cas_vzletu: maVzlet ? casVzletu.toISOString() : null,
        cas_pristani: ukonceny ? casPristani.toISOString() : null,
        misto_pristani_id: ukonceny && mistoPristani ? Number(mistoPristani) : null,
        pocet_tg: ukonceny ? tg : 0,
        kratky_let: kratkyLet ? kratky : '',
        verze: let_.verze,
        duvod: duvod ?? '',
        poznamka,
      }
      return opravitLet(let_.id, data)
    },
    onSuccess: (l) => {
      notifications.show({ message: `Let ${l.imatrikulace} opraven.`, color: 'green' })
      void klient.invalidateQueries({ predicate: jeLetovyDotaz })
      onZavrit()
    },
    onError: (e) => {
      notifications.show({ message: e.message, color: 'red', autoClose: 8000 })
      if (e instanceof ApiChyba && e.kod === 'zmeneno') {
        void klient.invalidateQueries({ predicate: jeLetovyDotaz })
        onZavrit()
      }
    },
  })

  if (!c || !letadlo) return null
  const kompletni = pic !== null && (!sloty.druhy || druhy !== null) && duvod !== null

  return (
    <Modal opened onClose={onZavrit} title={`Oprava letu ${let_.imatrikulace}`} fullScreen={mobil} size="lg">
      <Stack>
        <Select
          label="Letadlo"
          size="md"
          searchable={hledani}
          data={c.letadla
            .filter((l) => !tah || l.vlecne)
            .map((l) => ({ value: String(l.id), label: `${l.imatrikulace} (${l.typ})` }))}
          value={letadloId}
          onChange={(v) => {
            if (!v) return
            setLetadloId(v)
            setUlohaId(null)
          }}
          allowDeselect={false}
        />
        {tah && <Text fz="sm">Let vlečného letadla{let_.vlek ? ` – ${let_.vlek}` : ''}</Text>}
        <Stack gap={4} display={tah ? 'none' : undefined}>
          <Text fz="sm" fw={500}>
            Účel
          </Text>
          <SimpleGrid cols={2} spacing="xs">
            {UCELY.map((u) => (
              <Button
                key={u.hodnota}
                variant={u.hodnota === ucel ? 'filled' : 'default'}
                onClick={() => {
                  if (u.hodnota === ucel) return
                  setUcel(u.hodnota)
                  setDruhy(null)
                  setClenove([])
                  setUlohaId(null)
                }}
              >
                {u.nazev}
              </Button>
            ))}
          </SimpleGrid>
        </Stack>
        <Select
          label={sloty.pic.popis}
          size="md"
          searchable={hledani}
          data={nabidka(c.osoby, letadlo.kategorie, sloty.pic, ucel === 'prezkouseni', veVzduchu)}
          value={pic}
          onChange={(v) => {
            setPic(v)
            setClenove((cl) => cl.filter((id) => id !== v))
          }}
        />
        {ucel === 'normalni' && !tah && (
          <DalsiClenove
            osoby={c.osoby}
            pic={pic}
            hodnota={clenove}
            onZmena={setClenove}
            onProhodit={() => {
              setClenove(pic ? [pic] : [])
              setPic(clenove[0])
            }}
            veVzduchu={veVzduchu}
            hledani={hledani}
            maxPocet={Math.max(0, letadlo.pocet_mist - 1 - hoste)}
          />
        )}
        {sloty.druhy && (
          <Select
            label={sloty.druhy.popis}
            size="md"
            searchable={hledani}
            data={nabidka(
              c.osoby.filter((o) => String(o.id) !== pic),
              letadlo.kategorie,
              sloty.druhy,
              false,
              veVzduchu,
            )}
            value={druhy}
            onChange={setDruhy}
          />
        )}
        {ucel === 'normalni' && !tah && (
          <Pocitadlo
            popis="Hosté – nečlenové aeroklubu (počet)"
            popisek="Jen lidé mimo aeroklub, eviduje se počet bez jmen."
            hodnota={hoste}
            onZmena={setHoste}
            max={Math.max(0, letadlo.pocet_mist - 1 - clenove.length)}
          />
        )}
        <Select
          label="Platí"
          size="md"
          data={[...moznostiPlatce, { value: 'aeroklub', label: 'Aeroklub' }]}
          value={platceOk ? platce : null}
          onChange={setPlatce}
          placeholder="Podle účelu letu"
        />
        <Select
          display={tah ? 'none' : undefined}
          label="Úloha"
          size="md"
          searchable={hledani}
          clearable
          placeholder="Bez úlohy"
          data={ulohy}
          value={ulohaId}
          onChange={setUlohaId}
        />
        {let_.zpusob_vzletu === 'vlek' && (
          <Text fz="sm">Vzlet ve vleku ({let_.vlek}) – opravou nejde změnit.</Text>
        )}
        {letadlo.kategorie === 'kluzak' && let_.zpusob_vzletu !== 'vlek' && (
          <SegmentedControl
            value={zpusob}
            onChange={setZpusob}
            data={[
              { value: 'navijak', label: 'Naviják' },
              { value: 'autostart', label: 'Autostart' },
            ]}
          />
        )}
        <Select
          label="Místo vzletu"
          size="md"
          data={letiste}
          value={mistoVzletu}
          onChange={(v) => v && setMistoVzletu(v)}
          allowDeselect={false}
        />
        {maVzlet && (
          <CasVolba popis="Vzlet (UTC)" hodnota={casVzletu} onZmena={setCasVzletu} ted={ted} />
        )}
        {ukonceny && (
          <>
            <CasVolba popis="Přistání (UTC)" hodnota={casPristani} onZmena={setCasPristani} ted={ted} />
            <Select
              label="Místo přistání"
              size="md"
              data={letiste}
              value={mistoPristani}
              onChange={setMistoPristani}
              allowDeselect={false}
            />
            <Pocitadlo popis="Touch-and-go" hodnota={tg} onZmena={setTg} />
            {kratkyLet && casPristani >= casVzletu && (
              <SegmentedControl
                value={kratky}
                onChange={setKratky}
                data={[
                  { value: 'start_bez_doby', label: 'Start, doba 0' },
                  { value: 'normalni', label: 'Normální let' },
                ]}
              />
            )}
            {casPristani < casVzletu && <Alert color="red">Přistání je dřív než vzlet.</Alert>}
          </>
        )}
        <Select
          label="Důvod opravy"
          size="md"
          required
          data={c.duvody_opravy.map((d) => ({ value: d.hodnota, label: d.nazev }))}
          value={duvod}
          onChange={setDuvod}
        />
        <TextInput
          label="Poznámka (nepovinná)"
          size="md"
          value={poznamka}
          onChange={(e) => setPoznamka(e.currentTarget.value)}
          maxLength={300}
        />
        <Group grow>
          <Button variant="default" size="md" onClick={onZavrit}>
            Zpět
          </Button>
          <Button
            size="md"
            loading={ulozeni.isPending}
            disabled={!kompletni || (ukonceny && casPristani < casVzletu)}
            onClick={() => ulozeni.mutate()}
          >
            Uložit opravu
          </Button>
        </Group>
      </Stack>
    </Modal>
  )
}
