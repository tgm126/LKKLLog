import {
  Alert,
  Anchor,
  Button,
  Checkbox,
  CloseButton,
  Container,
  Grid,
  Group,
  Loader,
  NumberInput,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type ReactNode, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";

import {
  KATEGORIE_LETADLA,
  type KartaLetadla as Karta,
  type KartaLetadlaIn,
  nactiKartuLetadla,
  nactiVolbyLetadel,
  type TerminData,
  ulozitKartuLetadla,
  type VolbyLetadel,
} from "../api/letadla";
import { doba } from "../cas";
import { BARVA_STAVU } from "../stav";

const PRAZDNA: KartaLetadlaIn = {
  imatrikulace: "",
  typ_letadla_id: null,
  pocet_mist: 2,
  max_doba_min: null,
  vlecne: false,
  soukrome: false,
  aktivni: true,
  poradi: 100,
  nalet_pocatek_min: 0,
  starty_pocatek: 0,
  stav_k: null,
  terminy: [],
};

/** Řádek termínu ve formuláři; `id` jen u uloženého (kvůli zobrazení stavu). */
type Radek = TerminData & { id?: number };

const zKarty = (k: Karta): KartaLetadlaIn & { terminy: Radek[] } => ({
  ...k,
  terminy: k.terminy.map(({ id, druh_id, datum, pri_naletu_h, poznamka }) => ({
    id,
    druh_id,
    datum,
    pri_naletu_h,
    poznamka,
  })),
});

/** Prázdné pole čísla = null. */
const cislo = (v: number | string) => (v === "" ? null : Number(v));

/** Nadpis oddílu karty – jedna menší velikost, šedě (jako na kartě osoby). */
function Oddil({
  nazev,
  children,
  akce,
}: {
  nazev: string;
  children: ReactNode;
  akce?: ReactNode;
}) {
  return (
    <Stack gap={6}>
      <Group justify="space-between" wrap="nowrap" mih={22}>
        <Text fz="xs" fw={600} c="dimmed">
          {nazev}
        </Text>
        {akce}
      </Group>
      {children}
    </Stack>
  );
}

function Terminy({
  volby,
  terminy,
  ulozene,
  onZmena,
}: {
  volby: VolbyLetadel;
  terminy: Radek[];
  ulozene: Karta | null;
  onZmena: (t: Radek[]) => void;
}) {
  const nazev = (druh_id: number) =>
    volby.druhy_terminu.find((d) => d.id === druh_id)?.nazev ?? "?";
  const zmenit = (i: number, zmena: Partial<Radek>) =>
    // Změněný řádek ztrácí uložený stav (spočítá se po uložení).
    onZmena(
      terminy.map((t, j) => (j === i ? { ...t, ...zmena, id: undefined } : t)),
    );
  const stav = (t: Radek) => ulozene?.terminy.find((u) => u.id === t.id);
  return (
    <Oddil
      nazev="Termíny"
      akce={
        <Select
          size="xs"
          w={190}
          placeholder="+ přidat termín"
          aria-label="Přidat termín"
          data={volby.druhy_terminu
            .filter((d) => d.aktivni)
            .map((d) => ({ value: String(d.id), label: d.nazev }))}
          value={null}
          onChange={(v) =>
            v &&
            onZmena([
              ...terminy,
              {
                druh_id: Number(v),
                datum: null,
                pri_naletu_h: null,
                poznamka: "",
              },
            ])
          }
        />
      }
    >
      {terminy.length === 0 ? (
        <Text fz="sm" c="dimmed">
          žádné
        </Text>
      ) : (
        <Table.ScrollContainer minWidth={560}>
          <Table
            fz="sm"
            verticalSpacing={4}
            horizontalSpacing={6}
            withTableBorder
          >
            <Table.Thead>
              <Table.Tr>
                {["Termín", "Do data", "Při náletu [h]", "Poznámka", ""].map(
                  (n) => (
                    <Table.Th key={n} fz="xs" c="dimmed" fw={500}>
                      {n}
                    </Table.Th>
                  ),
                )}
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {terminy.map((t, i) => {
                const s = stav(t);
                return (
                  <Table.Tr key={i}>
                    <Table.Td miw={150}>
                      <Text fz="sm">{nazev(t.druh_id)}</Text>
                      {s && (
                        <Text
                          fz="xs"
                          c={s.stav === "ok" ? "dimmed" : BARVA_STAVU[s.stav]}
                        >
                          {s.text}
                        </Text>
                      )}
                    </Table.Td>
                    <Table.Td>
                      <TextInput
                        type="date"
                        size="xs"
                        w={132}
                        aria-label={`${nazev(t.druh_id)} do data`}
                        value={t.datum ?? ""}
                        onChange={(e) =>
                          zmenit(i, { datum: e.currentTarget.value || null })
                        }
                      />
                    </Table.Td>
                    <Table.Td>
                      <NumberInput
                        size="xs"
                        w={80}
                        min={0}
                        hideControls
                        aria-label={`${nazev(t.druh_id)} při náletu`}
                        value={t.pri_naletu_h ?? ""}
                        onChange={(v) => zmenit(i, { pri_naletu_h: cislo(v) })}
                      />
                    </Table.Td>
                    <Table.Td>
                      <TextInput
                        size="xs"
                        miw={100}
                        aria-label={`${nazev(t.druh_id)} poznámka`}
                        value={t.poznamka}
                        onChange={(e) =>
                          zmenit(i, { poznamka: e.currentTarget.value })
                        }
                      />
                    </Table.Td>
                    <Table.Td>
                      <CloseButton
                        size="sm"
                        aria-label={`Odebrat ${nazev(t.druh_id)}`}
                        onClick={() =>
                          onZmena(terminy.filter((_, j) => j !== i))
                        }
                      />
                    </Table.Td>
                  </Table.Tr>
                );
              })}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      )}
      <Text fz="xs" c="dimmed">
        Stačí datum, nebo celkový nálet; při obou platí, co nastane dřív.
      </Text>
    </Oddil>
  );
}

function Formular({
  id,
  karta,
  volby,
}: {
  id: number | null;
  karta: Karta | null;
  volby: VolbyLetadel;
}) {
  const klient = useQueryClient();
  const navigate = useNavigate();
  const [ulozene, setUlozene] = useState(karta);
  const [data, setData] = useState<KartaLetadlaIn & { terminy: Radek[] }>(() =>
    karta ? zKarty(karta) : PRAZDNA,
  );
  const nastav = (zmena: Partial<KartaLetadlaIn>) =>
    setData({ ...data, ...zmena });

  const ulozeni = useMutation({
    mutationFn: () =>
      ulozitKartuLetadla(id, {
        ...data,
        terminy: data.terminy.map(
          ({ druh_id, datum, pri_naletu_h, poznamka }) => ({
            druh_id,
            datum,
            pri_naletu_h,
            poznamka,
          }),
        ),
      }),
    onSuccess: (k) => {
      klient.setQueryData(["sprava", "letadlo", k.id], k);
      void klient.invalidateQueries({ queryKey: ["sprava", "letadla"] });
      void klient.invalidateQueries({ queryKey: ["ciselniky"] }); // letadla v průvodci
      notifications.show({ message: "Uloženo.", color: "green" });
      if (id) {
        setUlozene(k);
        setData(zKarty(k));
      } else navigate(`/letadla/${k.id}`, { replace: true });
    },
    onError: (e) => notifications.show({ message: e.message, color: "red" }),
  });

  const typ = volby.typy.find((t) => t.id === data.typ_letadla_id);
  const typy = Object.entries(
    volby.typy
      .filter((t) => t.aktivni || t.id === data.typ_letadla_id)
      .reduce<Record<string, { value: string; label: string }[]>>((g, t) => {
        (g[KATEGORIE_LETADLA[t.kategorie] ?? t.kategorie] ??= []).push({
          value: String(t.id),
          label: t.nazev,
        });
        return g;
      }, {}),
  ).map(([group, items]) => ({ group, items }));

  const ulozit = (
    <Button
      size="compact-sm"
      loading={ulozeni.isPending}
      onClick={() => ulozeni.mutate()}
    >
      Uložit
    </Button>
  );

  return (
    <Stack gap="md">
      <Group justify="space-between" wrap="nowrap">
        <div>
          <Anchor component={Link} to="/letadla" fz="xs">
            ← Letadla
          </Anchor>
          <Title order={3}>
            {id ? `${ulozene?.imatrikulace} ${ulozene?.typ}` : "Nové letadlo"}
          </Title>
        </div>
        {ulozit}
      </Group>
      <Grid gap="lg">
        <Grid.Col span={{ base: 12, md: 5 }}>
          <Stack gap="md">
            <Oddil nazev="Údaje">
              <Group grow gap="xs" align="flex-start">
                <TextInput
                  size="sm"
                  label="Imatrikulace"
                  placeholder="OK-0815"
                  value={data.imatrikulace}
                  onChange={(e) =>
                    nastav({ imatrikulace: e.currentTarget.value })
                  }
                />
                <Select
                  size="sm"
                  label={
                    typ
                      ? `Typ (${KATEGORIE_LETADLA[typ.kategorie] ?? typ.kategorie})`
                      : "Typ"
                  }
                  searchable
                  data={typy}
                  value={
                    data.typ_letadla_id ? String(data.typ_letadla_id) : null
                  }
                  onChange={(v) =>
                    nastav({ typ_letadla_id: v ? Number(v) : null })
                  }
                />
              </Group>
              <Group grow gap="xs" align="flex-start">
                <NumberInput
                  size="sm"
                  label="Počet míst"
                  min={1}
                  hideControls
                  value={data.pocet_mist}
                  onChange={(v) => nastav({ pocet_mist: Number(v) || 1 })}
                />
                <NumberInput
                  size="sm"
                  label="Max. doba [min]"
                  placeholder="u kluzáků prázdné"
                  min={1}
                  hideControls
                  value={data.max_doba_min ?? ""}
                  onChange={(v) => nastav({ max_doba_min: cislo(v) })}
                />
                <NumberInput
                  size="sm"
                  label="Pořadí"
                  min={0}
                  hideControls
                  value={data.poradi}
                  onChange={(v) => nastav({ poradi: Number(v) || 0 })}
                />
              </Group>
              <Group gap="md">
                <Checkbox
                  size="sm"
                  label="Aktivní"
                  checked={data.aktivni}
                  onChange={(e) => nastav({ aktivni: e.currentTarget.checked })}
                />
                <Checkbox
                  size="sm"
                  label="Vlečné"
                  checked={data.vlecne}
                  onChange={(e) => nastav({ vlecne: e.currentTarget.checked })}
                />
                <Checkbox
                  size="sm"
                  label="Soukromé (bez exportu pro účetnictví)"
                  checked={data.soukrome}
                  onChange={(e) =>
                    nastav({ soukrome: e.currentTarget.checked })
                  }
                />
              </Group>
            </Oddil>
            <Oddil nazev="Provozní deník (stav při spuštění ostrého provozu)">
              <Group gap="xs" align="flex-start">
                <TextInput
                  type="date"
                  size="sm"
                  w={150}
                  label="Stav ke dni"
                  value={data.stav_k ?? ""}
                  onChange={(e) =>
                    nastav({ stav_k: e.currentTarget.value || null })
                  }
                />
                <NumberInput
                  size="sm"
                  label="Nálet [h]"
                  w={90}
                  min={0}
                  hideControls
                  value={Math.floor(data.nalet_pocatek_min / 60)}
                  onChange={(v) =>
                    nastav({
                      nalet_pocatek_min:
                        (Number(v) || 0) * 60 + (data.nalet_pocatek_min % 60),
                    })
                  }
                />
                <NumberInput
                  size="sm"
                  label="[min]"
                  w={60}
                  min={0}
                  max={59}
                  hideControls
                  value={data.nalet_pocatek_min % 60}
                  onChange={(v) =>
                    nastav({
                      nalet_pocatek_min:
                        Math.floor(data.nalet_pocatek_min / 60) * 60 +
                        Math.min(59, Number(v) || 0),
                    })
                  }
                />
                <NumberInput
                  size="sm"
                  label="Starty"
                  w={90}
                  min={0}
                  hideControls
                  value={data.starty_pocatek}
                  onChange={(v) => nastav({ starty_pocatek: Number(v) || 0 })}
                />
              </Group>
              {ulozene && !ulozene.chybi_denik && (
                <Text fz="sm">
                  Celkem teď {doba(ulozene.nalet_min)} · {ulozene.starty} startů{" "}
                  <Text span fz="xs" c="dimmed">
                    (deník + lety z evidence po dni stavu)
                  </Text>
                </Text>
              )}
              {(!ulozene || ulozene.chybi_denik) && (
                <Text fz="xs" c="orange">
                  Bez stavu deníku nesedí celkový nálet ani termíny podle
                  náletu.
                </Text>
              )}
            </Oddil>
          </Stack>
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 7 }}>
          <Terminy
            volby={volby}
            terminy={data.terminy}
            ulozene={ulozene}
            onZmena={(terminy) => nastav({ terminy })}
          />
        </Grid.Col>
      </Grid>
      <Group justify="flex-end">{ulozit}</Group>
    </Stack>
  );
}

/** Karta letadla: údaje, typ z číselníku, stav deníku a termíny na jednom místě. */
export function KartaLetadla() {
  const { id: parametr } = useParams();
  const id = parametr && parametr !== "nove" ? Number(parametr) : null;
  const volby = useQuery({
    queryKey: ["sprava", "volby-letadel"],
    queryFn: nactiVolbyLetadel,
  });
  const karta = useQuery({
    queryKey: ["sprava", "letadlo", id],
    queryFn: () => nactiKartuLetadla(id!),
    enabled: id !== null,
  });
  const chyba = volby.error ?? karta.error;
  return (
    <Container size="lg" pb="xl">
      {chyba && <Alert color="red">{chyba.message}</Alert>}
      {(volby.isPending || (id !== null && karta.isPending)) && !chyba && (
        <Loader size="sm" />
      )}
      {volby.data && (id === null || karta.data) && (
        <Formular
          key={id ?? "nove"}
          id={id}
          karta={karta.data ?? null}
          volby={volby.data}
        />
      )}
    </Container>
  );
}
