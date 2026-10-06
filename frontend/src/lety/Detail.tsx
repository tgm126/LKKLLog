import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { useNavigate, useParams } from "react-router";

import { poslat } from "../api";
import { doba, hodinyMinuty, hodinyMinutySekundy, ted } from "../cas";
import { Hlaska } from "../komponenty/Hlaska";
import { Blok, Obrazovka } from "../komponenty/Obrazovka";
import { Oznameni, useOznamit } from "../komponenty/Oznameni";
import { Stitek, type BarvaStitku } from "../komponenty/Stitek";
import { Tlacitko } from "../komponenty/Tlacitko";
import { useJa } from "../uzivatel";
import { useAkceLetu, type Provedeno } from "./akce";
import { useDetail, useNabidky, type DetailLetu, type Nabidky, type Stav } from "./api";
import { jmeno, PIC_NAZEV, VolbaPoctu, VolbaUlohy } from "./Pruvodce";
import { denUtc, minutyUtc, VyberCasu } from "./VyberCasu";
import { VyberMista } from "./VyberMista";
import "./Detail.css";
import "./Volby.css";

// Detail letu přes celou obrazovku (docs/modul-lety.md 3.5): bloky Posádka · Let · Časy
// a místa · Platba · Poznámka · Evidence. Ťuknutí na údaj ho upraví na místě.

const STAV: Record<Stav, [string, BarvaStitku | undefined]> = {
  VE_VZDUCHU: ["Ve vzduchu", "zeleny"],
  NAPLANOVAN: ["Naplánovaný", "modry"],
  UKONCEN: ["Ukončený", undefined],
  ZRUSEN: ["Zrušený", undefined],
};

/** Údaj „popisek – hodnota“; s úpravou je to tlačítko a pod ním se otevře úprava. */
function Udaj({
  popisek,
  hodnota,
  upravit,
  otevreno,
  children,
}: {
  popisek: string;
  hodnota: ReactNode;
  upravit?: () => void;
  otevreno?: boolean;
  children?: ReactNode;
}) {
  const obsah = (
    <>
      <span className="udaj-popisek">{popisek}</span>
      <span>{hodnota ?? <span className="seda">—</span>}</span>
    </>
  );
  return (
    <>
      {upravit ? (
        <button type="button" className="udaj" aria-expanded={otevreno} onClick={upravit}>
          {obsah}
        </button>
      ) : (
        <div className="udaj">{obsah}</div>
      )}
      {otevreno && <div className="uprava">{children}</div>}
    </>
  );
}

export function Detail() {
  const letId = Number(useParams().id);
  const { data: let_, error } = useDetail(letId);
  const nabidky = useNabidky().data;
  const navigate = useNavigate();
  const zpet = () => navigate("/");
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
  const ja = useJa().data!;
  const navigate = useNavigate();
  const qc = useQueryClient();
  const oznamit = useOznamit();
  const [upravuji, setUpravuji] = useState<string | null>(null);
  const prepnout = (klic: string) => () => setUpravuji(upravuji === klic ? null : klic);

  const upravit = useMutation({
    mutationFn: (zmeny: Record<string, unknown>) =>
      poslat<DetailLetu>(`/lety/${l.id}`, { verze: l.verze, ...zmeny }),
    onSuccess: (novy) => {
      qc.setQueryData(["let", l.id], novy);
      qc.invalidateQueries({ queryKey: ["lety"] });
      setUpravuji(null);
    },
    onError: (e) => {
      oznamit({ text: e.message, chyba: true });
      qc.invalidateQueries({ queryKey: ["let", l.id] });
    },
  });
  const ulozit = (zmeny: Record<string, unknown>) => upravit.mutate(zmeny);

  const lzeUpravit = l.stav !== "ZRUSEN";
  const pristal = l.stav === "UKONCEN";
  const u = (klic: string, povoleno = true) =>
    lzeUpravit && povoleno ? { upravit: prepnout(klic), otevreno: upravuji === klic } : {};

  const posadkaIds = l.posadka.map((c) => c.osoba_id);
  /** Výběr osoby: Já, pak všichni (kromě vyloučených). */
  const vyberOsoby = (vyloucit: number[], vybrat: (id: number) => void) => (
    <div className="navrhy">
      {[...nabidky.osoby]
        .sort((a, b) => Number(b.id === ja.osoba_id) - Number(a.id === ja.osoba_id))
        .filter((o) => !vyloucit.includes(o.id))
        .map((o) => (
          <Tlacitko key={o.id} varianta="obrys" onClick={() => vybrat(o.id)}>
            {o.id === ja.osoba_id ? `Já (${jmeno(o)})` : jmeno(o)}
          </Tlacitko>
        ))}
    </div>
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

  const ulohy = nabidky.ulohy.filter(
    (x) =>
      x.ucel_id === l.ucel_id && (x.kategorie_kod === null || x.kategorie_kod === l.kategorie_kod),
  );
  const ucel = nabidky.ucely.find((x) => x.id === l.ucel_id);
  const platce = l.plati_aeroklub
    ? "Aeroklub"
    : l.platce_jmeno && `${l.platce_jmeno} ${l.platce_prijmeni}`;
  const [stav, barva] = l.varovani ? (["Ve vzduchu", "cerveny"] as const) : STAV[l.stav];

  return (
    <Obrazovka
      zpet={zpet}
      zpetPopis="Zpět"
      nadpis={
        <>
          {l.rejstrik}{" "}
          <span className="male seda">
            {l.typ} · {l.kategorie}
          </span>
        </>
      }
      vpravo={<Stitek barva={barva}>{stav}</Stitek>}
      akce={<AkceDetailu let_={l} nabidky={nabidky} />}
    >
      {l.varovani && <p className="text-chyby">{l.varovani}</p>}

      <Blok nadpis="Posádka">
        {l.posadka.map((c) => (
          <Udaj
            key={c.funkce_id}
            popisek={c.funkce_kod === "PIC" ? (PIC_NAZEV[l.ucel_kod ?? ""] ?? "PIC") : c.funkce}
            hodnota={`${c.jmeno} ${c.prijmeni}`}
            {...u(`f${c.funkce_id}`)}
          >
            {vyberOsoby(posadkaIds, (id) =>
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
      </Blok>

      <Blok nadpis="Let">
        <Udaj popisek="Účel" hodnota={l.je_vlecny ? "vlek" : l.ucel} />
        {!l.je_vlecny && ulohy.length > 0 && (
          <Udaj popisek="Úloha" hodnota={l.uloha} {...u("uloha")}>
            <VolbaUlohy
              ulohy={ulohy}
              povinna={!!ucel?.uloha_povinna}
              vybrana={ulohy.find((x) => x.id === l.uloha_id)}
              vybrat={(id) => ulozit({ uloha_id: id ?? null })}
              menit
            />
          </Udaj>
        )}
        <Udaj popisek="Způsob vzletu" hodnota={l.zpusob_vzletu} />
        {l.vlek && (
          <Udaj
            popisek={l.je_vlecny ? "Vleče" : "Vlečná"}
            hodnota={`${l.vlek.rejstrik} · ${l.vlek.pilot}`}
            upravit={() => navigate(`/let/${l.vlek!.let_id}`)}
          />
        )}
      </Blok>

      <Blok nadpis="Časy a místa">
        <Udaj popisek="Místo vzletu" hodnota={l.misto_vzletu} {...u("misto_vzletu")}>
          <VyberMista
            nabidky={nabidky}
            ulozit={(id, popis) => ulozit({ misto_vzletu_id: id, misto_vzletu_popis: popis })}
          />
        </Udaj>
        {l.cas_vzletu && (
          <Udaj
            popisek="Vzlet"
            hodnota={<span className="cisla">{hodinyMinutySekundy(new Date(l.cas_vzletu))}</span>}
            {...u("cas_vzletu")}
          >
            <UpravaCasu
              nadpis="Vzlet"
              puvodni={minutyUtc(l.cas_vzletu)}
              zacatekDne={zacatekDne}
              limit={dnes ? minutyUtc(nyni) : 1439}
              ulozit={(iso) => ulozit({ cas_vzletu: iso })}
            />
          </Udaj>
        )}
        {l.tg.length > 0 && (
          <Udaj
            popisek="T&G"
            hodnota={
              <span className="cisla">
                {l.tg.length} · {l.tg.map((c) => hodinyMinuty(c)).join(", ")}
              </span>
            }
          />
        )}
        {pristal && l.cas_pristani && (
          <>
            <Udaj
              popisek="Přistání"
              hodnota={
                <span className="cisla">{hodinyMinutySekundy(new Date(l.cas_pristani))}</span>
              }
              {...u("cas_pristani")}
            >
              <UpravaCasu
                nadpis="Přistání"
                puvodni={minutyUtc(l.cas_pristani)}
                zacatekDne={zacatekDne}
                limit={dnes ? minutyUtc(nyni) : 1439}
                ulozit={(iso) => ulozit({ cas_pristani: iso })}
              />
            </Udaj>
            <Udaj popisek="Místo přistání" hodnota={l.misto_pristani} {...u("misto_pristani")}>
              <VyberMista
                nabidky={nabidky}
                ulozit={(id, popis) =>
                  ulozit({ misto_pristani_id: id, misto_pristani_popis: popis })
                }
              />
            </Udaj>
            <Udaj
              popisek="Doba"
              hodnota={<b className="cisla">{doba(l.doba_uctovana_min ?? 0)}</b>}
            />
            <Udaj popisek="Přistání celkem" hodnota={l.pocet_pristani} {...u("pocet_pristani")}>
              <VolbaPoctu
                pocet={5}
                vybrano={l.pocet_pristani}
                vybrat={(n) => ulozit({ pocet_pristani: n })}
              />
            </Udaj>
          </>
        )}
      </Blok>

      <Blok nadpis="Platba">
        <Udaj popisek="Platí" hodnota={platce} {...u("platce")}>
          <div className="navrhy">
            <Tlacitko varianta="obrys" onClick={() => ulozit({ plati_aeroklub: true })}>
              Aeroklub
            </Tlacitko>
          </div>
          {vyberOsoby(l.plati_aeroklub ? [] : [l.platce_id ?? -1], (id) =>
            ulozit({ platce_id: id }),
          )}
        </Udaj>
      </Blok>

      <Blok nadpis="Poznámka">
        <Udaj
          popisek="Poznámka"
          hodnota={l.poznamka ?? <span className="seda">ťuknutím přidat</span>}
          {...u("poznamka")}
        >
          <UpravaPoznamky puvodni={l.poznamka ?? ""} ulozit={(p) => ulozit({ poznamka: p })} />
        </Udaj>
      </Blok>

      <Blok nadpis="Evidence">
        <Udaj
          popisek="Založil"
          hodnota={`${l.zalozil} · ${hodinyMinuty(l.zalozeno)}${l.dodatecne ? " (dodatečně)" : ""}`}
        />
        {l.zruseno && (
          <Udaj
            popisek="Zrušil"
            hodnota={`${l.zrusil ?? "—"} · ${hodinyMinuty(l.zruseno)} · ${l.duvod_zruseni}`}
          />
        )}
        {l.historie.slice(1).map((h, i) => (
          <Udaj
            key={i}
            popisek={hodinyMinutySekundy(new Date(h.kdy))}
            hodnota={
              <>
                {h.akce} · {h.kdo}
                {h.popis && <span className="udaj-pod">{h.popis}</span>}
              </>
            }
          />
        ))}
      </Blok>
    </Obrazovka>
  );
}

// --- úpravy na místě -------------------------------------------------------------------------

function UpravaCasu({
  nadpis,
  puvodni,
  zacatekDne,
  limit,
  ulozit,
}: {
  nadpis: string;
  puvodni: number;
  zacatekDne: number;
  limit: number;
  ulozit: (iso: string) => void;
}) {
  const [min, setMin] = useState(puvodni);
  const [otevreno, setOtevreno] = useState(false);
  const { iso, mistni } = denUtc(zacatekDne);
  return (
    <>
      <VyberCasu
        nadpis={nadpis}
        min={min}
        otevreno={otevreno}
        prepnout={() => setOtevreno(!otevreno)}
        nastavit={(m) => {
          setMin(m);
          setOtevreno(false);
        }}
        limit={limit}
        mistni={mistni}
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

function AkceDetailu({ let_: l, nabidky }: { let_: DetailLetu; nabidky: Nabidky }) {
  const { provest, pristat, dialog, probiha } = useAkceLetu();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const oznamit = useOznamit();
  const [rusim, setRusim] = useState(false);
  const zaneprazdnen = probiha?.letId === l.id;

  const prikaz = useMutation({
    mutationFn: (a: { cesta: string; data?: unknown }) =>
      poslat<Provedeno>(`/lety/${l.id}/${a.cesta}`, a.data),
    onSuccess: async (p, a) => {
      // Přehled letů se načte hned (i když teď není na obrazovce), aby po návratu na něj
      // nebyl vidět starý stav.
      await qc.invalidateQueries({ queryKey: ["lety"], refetchType: "all" });
      qc.invalidateQueries({ queryKey: ["let"] });
      setRusim(false);
      if (a.cesta === "dalsi") {
        oznamit({ text: `${p.rejstrik} naplánován` });
        navigate("/");
      } else {
        oznamit({ text: `${p.rejstrik} ${a.cesta === "zrusit" ? "zrušen" : "obnoven"}` });
      }
    },
    onError: (e) => oznamit({ text: e.message, chyba: true }),
  });

  if (rusim) {
    return (
      <>
        <span className="nadpisek">Důvod zrušení</span>
        <div className="navrhy">
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

  return (
    <>
      {dialog}
      <Oznameni />
      {l.stav === "VE_VZDUCHU" && (
        <div className="akce-vedle">
          {l.kategorie_kod !== "KLUZAK" && (
            <Tlacitko varianta="svetle" disabled={zaneprazdnen} onClick={() => provest(l.id, "tg")}>
              T&amp;G <span className="cisla">{l.tg.length}</span>
            </Tlacitko>
          )}
          <Tlacitko
            varianta="zelene"
            hlavni
            disabled={zaneprazdnen}
            onClick={() => pristat(l)}
          >
            Přistál
          </Tlacitko>
        </div>
      )}
      {l.stav === "NAPLANOVAN" && (
        <Tlacitko
          varianta="modre"
          hlavni
          disabled={zaneprazdnen}
          onClick={() => provest(l.id, "vzlet")}
        >
          Vzlet
        </Tlacitko>
      )}
      {l.stav === "UKONCEN" && !l.je_vlecny && (
        <Tlacitko
          varianta="obrys"
          disabled={prikaz.isPending}
          onClick={() => prikaz.mutate({ cesta: "dalsi" })}
        >
          Další let odsud
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
        <Tlacitko varianta="cervene" onClick={() => setRusim(true)}>
          Zrušit let
        </Tlacitko>
      )}
    </>
  );
}
