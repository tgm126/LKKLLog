import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate, useParams } from "react-router";

import { poslat } from "../api";
import { doba, hodinyMinuty, hodinyMinutySekundy, ted } from "../cas";
import { Hlaska } from "../komponenty/Hlaska";
import { Blok, Obrazovka, useZpet } from "../komponenty/Obrazovka";
import { Oznameni, useOznamit } from "../komponenty/Oznameni";
import { Stitek, type BarvaStitku } from "../komponenty/Stitek";
import { Tlacitko } from "../komponenty/Tlacitko";
import { useJa, useJenCteni } from "../uzivatel";
import { useAkceLetu, type Provedeno } from "./akce";
import { useDetail, useNabidky, type DetailLetu, type Nabidky, type Stav } from "./api";
import { PolovinaPasku, tridaPasku } from "./Pasek";
import { Udaj, Udaje } from "../komponenty/Udaje";
import {
  PIC_NAZEV,
  rychlaVolba,
  VolbaOsoby,
  VolbaPoctu,
  VolbaPrezkouseni,
  VolbaUlohy,
} from "./Volby";
import { denUtc, minutyUtc, VolbaCasu } from "./VyberCasu";
import { useMujProvoz } from "../provoz/api";
import { VyberMista } from "./VyberMista";
import "./Detail.css";

// Detail letu (docs/modul-lety.md 3.5, maketa lety-mobil-v4.html): nahoře pásek letu jako
// v přehledu, pod ním bloky Posádka a let · Časy a místa · Platba a poznámka · Evidence
// s poli ve dvou sloupcích. Ťuknutí na pole ho upraví pod ním. Na mobilu přes celou
// obrazovku; na desktopu tytéž bloky a akce v panelu zprava (deska/PanelDetailu.tsx).

const STAV: Record<Stav, [string, BarvaStitku | undefined]> = {
  VE_VZDUCHU: ["Ve vzduchu", "zeleny"],
  NAPLANOVAN: ["Naplánovaný", "modry"],
  UKONCEN: ["Ukončený", undefined],
  ZRUSEN: ["Zrušený", undefined],
};

/** 1 úprava, 2 úpravy, 5 úprav */
const uprav = (n: number) => `${n} ${n === 1 ? "úprava" : n < 5 ? "úpravy" : "úprav"}`;

export function Detail() {
  const letId = Number(useParams().id);
  const { data: let_, error } = useDetail(letId);
  const nabidky = useNabidky().data;
  // zpět tam, odkud přišel (Lety, Moje lety na zvoleném dni); otevřeno adresou = přehled
  const zpet = useZpet();
  if (!let_ || !nabidky) {
    return (
      <Obrazovka zpet={zpet} zpetPopis="Zpět" nadpis="Let">
        {error && <Hlaska>{error.message}</Hlaska>}
      </Obrazovka>
    );
  }
  return <DetailLetuObrazovka let_={let_} nabidky={nabidky} zpet={zpet} />;
}

function DetailLetuObrazovka({
  let_: l,
  nabidky,
  zpet,
}: {
  let_: DetailLetu;
  nabidky: Nabidky;
  zpet: () => void;
}) {
  const mojeKod = useMujProvoz().data?.letiste?.kod;
  const [stav, barva] = l.varovani ? (["Ve vzduchu", "cerveny"] as const) : STAV[l.stav];
  return (
    <Obrazovka
      zpet={zpet}
      zpetPopis="Zpět"
      nadpis="Let"
      vpravo={<Stitek barva={barva}>{stav}</Stitek>}
      akce={
        <>
          <Oznameni />
          <AkceDetailu let_={l} nabidky={nabidky} />
        </>
      }
    >
      <div className={`let panel-letu ${tridaPasku([l])}`}>
        {/* trasa na pásku jen tam, kde místo není moje letiště (jako v přehledu) */}
        <PolovinaPasku
          let={{
            ...l,
            misto_vzletu: l.misto_vzletu === mojeKod ? null : l.misto_vzletu,
            misto_pristani: l.misto_pristani === mojeKod ? null : l.misto_pristani,
          }}
        />
      </div>
      <DetailBloky let_={l} nabidky={nabidky} />
    </Obrazovka>
  );
}

/** Bloky detailu (Posádka a let · Časy a místa · Platba a poznámka · Evidence) s úpravou
 *  na místě – mobil i panel desktopu. */
export function DetailBloky({ let_: l, nabidky }: { let_: DetailLetu; nabidky: Nabidky }) {
  const ja = useJa().data!;
  const provoz = useMujProvoz().data;
  const vProvozu = { osoby: provoz?.osoby ?? [], jaId: ja.osoba_id };
  const navigate = useNavigate();
  const qc = useQueryClient();
  const oznamit = useOznamit();
  const [upravuji, setUpravuji] = useState<string | null>(null);
  const [historie, setHistorie] = useState(false);
  const prepnout = (klic: string) => () => setUpravuji(upravuji === klic ? null : klic);

  const upravit = useMutation({
    mutationFn: (zmeny: Record<string, unknown>) =>
      poslat<DetailLetu>(`/lety/${l.id}`, { verze: l.verze, ...zmeny }),
    onSuccess: (novy) => {
      qc.setQueryData(["let", l.id], novy);
      qc.invalidateQueries({ queryKey: ["lety"] });
      qc.invalidateQueries({ queryKey: ["nabidky"] }); // poloha letadla (místo přistání)
      setUpravuji(null);
    },
    onError: (e) => {
      oznamit({ text: e.message, chyba: true });
      qc.invalidateQueries({ queryKey: ["let", l.id] });
    },
  });
  const ulozit = (zmeny: Record<string, unknown>) => upravit.mutate(zmeny);

  // zrušený let jde jen obnovit; v relaci jen ke čtení se neupravuje nic
  const jenCteni = useJenCteni();
  const lzeUpravit = l.stav !== "ZRUSEN" && !jenCteni;
  const pristal = l.stav === "UKONCEN";
  const u = (klic: string, povoleno = true) =>
    lzeUpravit && povoleno ? { upravit: prepnout(klic), otevreno: upravuji === klic } : {};
  const posadkaIds = l.posadka.map((c) => c.osoba_id);
  // Typ přezkoušení (u přezkoušení místo úlohy, db/041): typy kategorie letadla; examinátor
  // (PIC) se nabízí podle zvoleného typu.
  const typyPrezkouseni =
    l.ucel_kod === "PREZKOUSENI"
      ? nabidky.prezkouseni.filter((t) => t.kategorie_kod === l.kategorie_kod)
      : [];
  const examinator = (funkceKod: string) =>
    funkceKod === "PIC" && l.ucel_kod === "PREZKOUSENI"
      ? { prezkouseni: l.prezkouseni_id ? [l.prezkouseni_id] : typyPrezkouseni.map((t) => t.id) }
      : {};
  const volbaOsoby = (
    funkceKod: string,
    vybrana: number | undefined,
    vybrat: (id: number) => void,
  ) => (
    <VolbaOsoby
      osoby={nabidky.osoby}
      jaId={ja.osoba_id}
      rychle={rychlaVolba(
        nabidky.osoby,
        {
          ucel: l.je_vlecny ? null : l.ucel_kod,
          funkce: funkceKod,
          kategorie: l.kategorie_kod,
          ...examinator(funkceKod),
        },
        [ja.osoba_id],
        vProvozu,
      )}
      filtr={vProvozu.osoby.length}
      vybrana={vybrana}
      vyloucit={posadkaIds.filter((id) => id !== vybrana)}
      vybrat={vybrat}
      menit
    />
  );

  // Časy: den letu (UTC) – úprava času nemění den.
  const zakladDne = new Date(l.cas_vzletu ?? l.zalozeno);
  const zacatekDne = Date.UTC(
    zakladDne.getUTCFullYear(),
    zakladDne.getUTCMonth(),
    zakladDne.getUTCDate(),
  );
  const nyni = ted();
  const dnes = zacatekDne === Date.UTC(nyni.getUTCFullYear(), nyni.getUTCMonth(), nyni.getUTCDate());
  const limit = dnes ? minutyUtc(nyni) : 1439;

  const ulohy = nabidky.ulohy.filter(
    (x) =>
      x.ucel_id === l.ucel_id && (x.kategorie_kod === null || x.kategorie_kod === l.kategorie_kod),
  );
  const ucel = nabidky.ucely.find((x) => x.id === l.ucel_id);
  const platce = l.plati_aeroklub
    ? "Aeroklub"
    : l.platce_jmeno && `${l.platce_jmeno} ${l.platce_prijmeni}`;
  const upravy = l.historie.slice(1);

  return (
    <>
      <Blok nadpis="Posádka a let">
        <Udaje>
          {l.posadka.map((c) => (
            <Udaj
              key={c.funkce_id}
              popisek={c.funkce_kod === "PIC" ? (PIC_NAZEV[l.ucel_kod ?? ""] ?? "PIC") : c.funkce}
              hodnota={`${c.jmeno} ${c.prijmeni}`}
              {...u(`f${c.funkce_id}`)}
            >
              {volbaOsoby(c.funkce_kod, c.osoba_id, (id) =>
                ulozit({
                  posadka: l.posadka.map((x) => ({
                    osoba_id: x.funkce_id === c.funkce_id ? id : x.osoba_id,
                    funkce_id: x.funkce_id,
                  })),
                }),
              )}
            </Udaj>
          ))}
          {l.pob_zadany !== null ? (
            <Udaj popisek="POB" hodnota={l.pob} {...u("pob", l.pocet_mist > 1)}>
              <VolbaPoctu pocet={l.pocet_mist} vybrano={l.pob} vybrat={(n) => ulozit({ pob: n })} />
            </Udaj>
          ) : (
            <Udaj popisek="POB" hodnota={`${l.pob} (z posádky)`} />
          )}
          <Udaj popisek="Účel" hodnota={l.je_vlecny ? "vlek" : l.ucel} />
          <Udaj popisek="Způsob vzletu" hodnota={l.zpusob_vzletu} />
          {!l.je_vlecny && ulohy.length > 0 && (
            <Udaj popisek="Úloha" hodnota={l.uloha} cely {...u("uloha")}>
              <VolbaUlohy
                ulohy={ulohy}
                povinna={!!ucel?.uloha_povinna}
                vybrana={ulohy.find((x) => x.id === l.uloha_id)}
                vybrat={(id) => ulozit({ uloha_id: id ?? null })}
                menit
              />
            </Udaj>
          )}
          {typyPrezkouseni.length > 0 && (
            <Udaj popisek="Přezkoušení" hodnota={l.prezkouseni} cely {...u("prezkouseni")}>
              <VolbaPrezkouseni
                typy={typyPrezkouseni}
                vybrany={typyPrezkouseni.find((t) => t.id === l.prezkouseni_id)}
                vybrat={(id) => ulozit({ prezkouseni_id: id })}
                menit
              />
            </Udaj>
          )}
          {l.vlek && (
            <Udaj
              popisek={l.je_vlecny ? "Vleče" : "Vlečná"}
              hodnota={`${l.vlek.rejstrik} · ${l.vlek.pilot}`}
              cely
              odkaz
              upravit={() => navigate(`/let/${l.vlek!.let_id}`)}
            />
          )}
        </Udaje>
      </Blok>

      <Blok nadpis="Časy a místa (UTC)">
        <Udaje>
          {l.cas_vzletu && (
            <Udaj
              popisek="Vzlet"
              hodnota={<span className="cisla">{hodinyMinutySekundy(new Date(l.cas_vzletu))}</span>}
              zvyraznit
              {...u("cas_vzletu")}
            >
              <UpravaCasu
                nazev="Vzlet"
                puvodni={minutyUtc(l.cas_vzletu)}
                zacatekDne={zacatekDne}
                limit={limit}
                ulozit={(iso) => ulozit({ cas_vzletu: iso })}
              />
            </Udaj>
          )}
          {pristal && l.cas_pristani && (
            <Udaj
              popisek="Přistání"
              hodnota={<span className="cisla">{hodinyMinutySekundy(new Date(l.cas_pristani))}</span>}
              zvyraznit
              {...u("cas_pristani")}
            >
              <UpravaCasu
                nazev="Přistání"
                puvodni={minutyUtc(l.cas_pristani)}
                zacatekDne={zacatekDne}
                limit={limit}
                ulozit={(iso) => ulozit({ cas_pristani: iso })}
              />
            </Udaj>
          )}
          <Udaj popisek="Místo vzletu" hodnota={l.misto_vzletu} {...u("misto_vzletu")}>
            <VyberMista
              nabidky={nabidky}
              ulozit={(id, popis) => ulozit({ misto_vzletu_id: id, misto_vzletu_popis: popis })}
            />
          </Udaj>
          {/* do přistání plán (cíl), po přistání skutečnost; jde upravit vždy (db/027) */}
          <Udaj popisek="Místo přistání" hodnota={l.misto_pristani} {...u("misto_pristani")}>
            <VyberMista
              nabidky={nabidky}
              ulozit={(id, popis) => ulozit({ misto_pristani_id: id, misto_pristani_popis: popis })}
            />
          </Udaj>
          {l.tg.length > 0 && (
            <Udaj
              popisek="T&G"
              hodnota={
                <span className="cisla">
                  {l.tg.length} · {l.tg.map((c) => hodinyMinuty(c)).join(", ")}
                </span>
              }
              cely
            />
          )}
          {pristal && (
            <Udaj
              popisek="Doba"
              hodnota={<span className="cisla">{doba(l.doba_uctovana_min ?? 0)}</span>}
              zvyraznit
            />
          )}
          {pristal && (
            <Udaj popisek="Přistání celkem" hodnota={l.pocet_pristani} {...u("pocet_pristani")}>
              <VolbaPoctu
                pocet={5}
                vybrano={l.pocet_pristani}
                vybrat={(n) => ulozit({ pocet_pristani: n })}
              />
            </Udaj>
          )}
        </Udaje>
      </Blok>

      <Blok nadpis="Platba a poznámka">
        <Udaje>
          <Udaj popisek="Platí" hodnota={platce} cely {...u("platce")}>
            <VolbaOsoby
              osoby={nabidky.osoby}
              jaId={ja.osoba_id}
              rychle={posadkaIds}
              vybrana={l.plati_aeroklub ? undefined : (l.platce_id ?? undefined)}
              vybrat={(id) => ulozit({ platce_id: id })}
              menit
              pred={
                <Tlacitko
                  aria-pressed={l.plati_aeroklub}
                  onClick={() => ulozit({ plati_aeroklub: true })}
                >
                  Aeroklub
                </Tlacitko>
              }
            />
          </Udaj>
          <Udaj
            popisek="Poznámka"
            hodnota={l.poznamka ?? <span className="seda">ťuknutím přidat</span>}
            cely
            {...u("poznamka")}
          >
            <UpravaPoznamky puvodni={l.poznamka ?? ""} ulozit={(p) => ulozit({ poznamka: p })} />
          </Udaj>
        </Udaje>
      </Blok>

      <Blok nadpis="Evidence">
        <Udaje>
          <Udaj
            popisek="Založil"
            hodnota={`${l.zalozil} · ${hodinyMinuty(l.zalozeno)}${l.dodatecne ? " (dodatečně)" : ""}`}
          />
          {upravy.length > 0 && (
            <Udaj
              popisek="Historie"
              hodnota={uprav(upravy.length)}
              upravit={() => setHistorie(!historie)}
              otevreno={historie}
            >
              {upravy.map((h, i) => (
                <p key={i}>
                  <span className="cisla">{hodinyMinutySekundy(new Date(h.kdy))}</span> · {h.akce} ·{" "}
                  {h.kdo}
                  {h.popis && <span className="udaj-pod">{h.popis}</span>}
                </p>
              ))}
            </Udaj>
          )}
          {l.zruseno && (
            <Udaj
              popisek="Zrušil"
              hodnota={`${l.zrusil ?? "—"} · ${hodinyMinuty(l.zruseno)} · ${l.duvod_zruseni}`}
              cely
            />
          )}
        </Udaje>
      </Blok>
    </>
  );
}

// --- úpravy na místě -------------------------------------------------------------------------

function UpravaCasu({
  nazev,
  puvodni,
  zacatekDne,
  limit,
  ulozit,
}: {
  nazev: string;
  puvodni: number;
  zacatekDne: number;
  limit: number;
  ulozit: (iso: string) => void;
}) {
  const [min, setMin] = useState(puvodni);
  const [aktivni, setAktivni] = useState<"cas" | null>("cas");
  const { iso, mistni } = denUtc(zacatekDne);
  return (
    <>
      <VolbaCasu
        pole={[{ klic: "cas", nazev, min }]}
        aktivni={aktivni}
        aktivovat={setAktivni}
        nastavit={(_, m, vybrano) => {
          setMin(m);
          if (vybrano) setAktivni(null);
        }}
        limit={limit}
        doplnek={<span className="male seda">místní {mistni(min)}</span>}
      />
      <Tlacitko varianta="modre" disabled={min === puvodni} onClick={() => ulozit(iso(min))}>
        Uložit čas
      </Tlacitko>
    </>
  );
}

function UpravaPoznamky({ puvodni, ulozit }: { puvodni: string; ulozit: (p: string) => void }) {
  const [text, setText] = useState(puvodni);
  return (
    <>
      <textarea
        className="poznamka"
        aria-label="Poznámka"
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <Tlacitko varianta="modre" disabled={text === puvodni} onClick={() => ulozit(text)}>
        Uložit poznámku
      </Tlacitko>
    </>
  );
}

// --- akce: podle stavu letu, zrušení s důvodem -------------------------------------------------

/** Akce detailu podle stavu letu (PŘISTÁL, T&G, VZLET, zrušení s důvodem, obnovení). */
export function AkceDetailu({ let_: l, nabidky }: { let_: DetailLetu; nabidky: Nabidky }) {
  const { provest, pristat, dialog, probiha } = useAkceLetu();
  const qc = useQueryClient();
  const oznamit = useOznamit();
  const [rusim, setRusim] = useState(false);
  const zaneprazdnen = probiha?.letId === l.id;
  const jenCteni = useJenCteni();

  const prikaz = useMutation({
    mutationFn: (a: { cesta: string; data?: unknown }) =>
      poslat<Provedeno>(`/lety/${l.id}/${a.cesta}`, a.data),
    onSuccess: async (p, a) => {
      // Přehled letů se načte hned (i když teď není na obrazovce), aby po návratu na něj
      // nebyl vidět starý stav.
      await qc.invalidateQueries({ queryKey: ["lety"], refetchType: "all" });
      qc.invalidateQueries({ queryKey: ["let"] });
      qc.invalidateQueries({ queryKey: ["nabidky"] });
      setRusim(false);
      oznamit({ text: `${p.rejstrik} ${a.cesta === "zrusit" ? "zrušen" : "obnoven"}` });
    },
    onError: (e) => oznamit({ text: e.message, chyba: true }),
  });

  if (jenCteni) return null;

  if (rusim) {
    return (
      <>
        <span className="nadpisek">Důvod zrušení</span>
        <div className="cipy">
          {nabidky.duvody_zruseni.map((d) => (
            <Tlacitko
              key={d.id}
              varianta="cervene"
              disabled={prikaz.isPending}
              onClick={() => prikaz.mutate({ cesta: "zrusit", data: { duvod_id: d.id } })}
            >
              {d.nazev}
            </Tlacitko>
          ))}
        </div>
        <Tlacitko varianta="obrys" onClick={() => setRusim(false)}>
          Nerušit
        </Tlacitko>
      </>
    );
  }

  const zrusit = (
    <Tlacitko varianta="cervene" onClick={() => setRusim(true)}>
      Zrušit let
    </Tlacitko>
  );
  return (
    <>
      {dialog}
      {l.stav === "VE_VZDUCHU" && (
        <div className="akce-vedle">
          {l.kategorie_kod !== "KLUZAK" && !l.je_vlecny && (
            <Tlacitko varianta="obrys" disabled={zaneprazdnen} onClick={() => provest(l.id, "tg")}>
              T&amp;G <span className="cisla">{l.tg.length}</span>
            </Tlacitko>
          )}
          <Tlacitko varianta="zelene" hlavni disabled={zaneprazdnen} onClick={() => pristat(l)}>
            Přistál
          </Tlacitko>
        </div>
      )}
      {l.stav === "NAPLANOVAN" && (
        <Tlacitko varianta="modre" hlavni disabled={zaneprazdnen} onClick={() => provest(l.id, "vzlet")}>
          Vzlet
        </Tlacitko>
      )}
      {l.stav === "ZRUSEN" ? (
        <Tlacitko
          varianta="obrys"
          disabled={prikaz.isPending}
          onClick={() => prikaz.mutate({ cesta: "obnovit" })}
        >
          Obnovit let
        </Tlacitko>
      ) : (
        zrusit
      )}
    </>
  );
}
