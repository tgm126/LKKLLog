import { useState, type ReactNode } from "react";
import { useNavigate } from "react-router";

import { Hlaska } from "../komponenty/Hlaska";
import { jakoTlacitko } from "../komponenty/klavesnice";
import { Blok, BlokTelo } from "../komponenty/Obrazovka";
import { Panel } from "../komponenty/Panel";
import { Pole } from "../komponenty/Pole";
import { Stitek } from "../komponenty/Stitek";
import { Tlacitko } from "../komponenty/Tlacitko";
import { Zaskrtavatka, Zaskrtavatko } from "../komponenty/Zaskrtavatko";
import {
  popisOsnovy,
  popisUlohy,
  useVycvik,
  useZmena,
  type Kategorie,
  type Osnova,
  type Typ,
  type Uloha,
  type Vycvik,
} from "./api";
import "../komponenty/Volby.css";
import "../lety/Volby.css";
import "./Vycvik.css";

// Editor výcviku – desktop, panel přes celou desku (docs/modul-osnovy.md, maketa
// docs/navrhy/osnovy-desktop-v2.html). Přepínač Osnovy a úlohy | Typy přezkoušení; vlevo
// tabulka se zaškrtávátky (každá změna se uloží hned), vpravo úprava vybrané položky a náhled,
// co uvidí pilot v novém letu. Pravidla (co by rozbilo staré lety) hlídá databáze.

type Vyber =
  | { druh: "osnova"; id: number }
  | { druh: "uloha"; id: number }
  | { druh: "nova-osnova" }
  | { druh: "nova-uloha"; osnovaId?: number };

type Zmena = ReturnType<typeof useZmena>;

export function EditorVycviku() {
  const { data, error } = useVycvik();
  const zmena = useZmena();
  const navigate = useNavigate();
  const zavrit = () => navigate("/");
  const [pohled, setPohled] = useState<"osnovy" | "typy">("osnovy");
  const [vyber, setVyber] = useState<Vyber | null>(null);
  const [typ, setTyp] = useState<number | "novy" | null>(null);

  const hlava = (
    <>
      <h2 className="velke tucne">Výcvik</h2>
      <div className="segmenty">
        <Tlacitko aria-pressed={pohled === "osnovy"} onClick={() => setPohled("osnovy")}>
          Osnovy a úlohy
        </Tlacitko>
        <Tlacitko aria-pressed={pohled === "typy"} onClick={() => setPohled("typy")}>
          Typy přezkoušení
        </Tlacitko>
      </div>
      {data && <span className="seda">{souhrn(data, pohled)}</span>}
    </>
  );
  if (!data) {
    return (
      <Panel nadpis="Výcvik" cely zavrit={zavrit} hlava={hlava}>
        {error && <Hlaska>{error.message}</Hlaska>}
      </Panel>
    );
  }
  return (
    <Panel
      nadpis="Výcvik"
      cely
      zavrit={zavrit}
      hlava={hlava}
      pata={
        pohled === "osnovy" ? (
          <>
            <Tlacitko varianta="obrys" onClick={() => setVyber({ druh: "nova-osnova" })}>
              Nová osnova
            </Tlacitko>
            <Tlacitko
              varianta="obrys"
              onClick={() => setVyber({ druh: "nova-uloha", osnovaId: osnovaVyberu(data, vyber)?.id })}
            >
              Nová úloha
            </Tlacitko>
            <span className="male seda">Každá změna se uloží hned a zapíše do historie.</span>
          </>
        ) : (
          <>
            <Tlacitko varianta="obrys" onClick={() => setTyp("novy")}>
              Nový typ přezkoušení
            </Tlacitko>
            <span className="male seda">Každá změna se uloží hned a zapíše do historie.</span>
          </>
        )
      }
    >
      {pohled === "osnovy" ? (
        <Osnovy data={data} zmena={zmena} vyber={vyber} setVyber={setVyber} />
      ) : (
        <Typy data={data} zmena={zmena} vybrany={typ} setVybrany={setTyp} />
      )}
    </Panel>
  );
}

function souhrn(data: Vycvik, pohled: "osnovy" | "typy") {
  if (pohled === "osnovy") {
    const ulohy = data.osnovy.flatMap((o) => o.ulohy.map((u) => [u, o] as const));
    const mimo = ulohy.filter(([u, o]) => nenabiziSe(u, o)).length;
    return `${data.osnovy.length} osnovy · ${ulohy.length} úloh${mimo ? ` · ${mimo} se nenabízí` : ""}`;
  }
  const bez = data.typy.filter((t) => t.platny && !examinatori(data, t).length).length;
  return `${data.typy.length} typů${bez ? ` · ${bez} bez examinátora` : ""}`;
}

/** Úloha bez účelu se nenabízí nikde (platná v platné osnově). */
const nenabiziSe = (u: Uloha, o: Osnova) => u.platny && o.platny && u.ucely.length === 0;
/** Účely, u kterých se úlohy nabízejí (u přezkoušení je místo úlohy typ přezkoušení). */
const ucelyUloh = (data: Vycvik) => data.ucely.filter((u) => u.kod !== "PREZKOUSENI");
const examinatori = (data: Vycvik, t: Typ) => data.examinatori.filter((e) => e.prezkouseni.includes(t.id));
const nazevKategorie = (data: Vycvik, id: number) =>
  data.kategorie.find((k) => k.id === id)?.nazev ?? "—";

function osnovaVyberu(data: Vycvik, vyber: Vyber | null): Osnova | undefined {
  if (vyber?.druh === "osnova") return data.osnovy.find((o) => o.id === vyber.id);
  if (vyber?.druh === "uloha") return data.osnovy.find((o) => o.ulohy.some((u) => u.id === vyber.id));
  return undefined;
}

// --- společné prvky ---------------------------------------------------------------------------

/** Zaškrtávátko v tabulce; částečně = jen některé úlohy osnovy. */
function Policko({
  ano,
  castecne = false,
  popis,
  zmenit,
}: {
  ano: boolean;
  castecne?: boolean;
  popis: string;
  zmenit: (ano: boolean) => void;
}) {
  return (
    <input
      type="checkbox"
      aria-label={popis}
      checked={ano}
      ref={(el) => {
        if (el) el.indeterminate = castecne;
      }}
      onChange={(e) => zmenit(e.target.checked)}
      onClick={(e) => e.stopPropagation()}
    />
  );
}

/** Pořadí ▲▼ (prohodí se sousedem). */
function Posun({ posunout }: { posunout: (smer: -1 | 1) => void }) {
  return (
    <span className="vycvik-posun">
      <button
        type="button"
        title="Výš"
        aria-label="Výš"
        onClick={(e) => (e.stopPropagation(), posunout(-1))}
      >
        ▲
      </button>
      <button
        type="button"
        title="Níž"
        aria-label="Níž"
        onClick={(e) => (e.stopPropagation(), posunout(1))}
      >
        ▼
      </button>
    </span>
  );
}

/** Textové pole, které se uloží po opuštění (nebo Enter), když se změnilo. */
function PoleUlozit({
  popisek,
  hodnota,
  ulozit,
  velka = false,
}: {
  popisek: string;
  hodnota: string;
  ulozit: (text: string) => void;
  velka?: boolean;
}) {
  const [text, setText] = useState(hodnota);
  return (
    <Pole
      popisek={popisek}
      value={text}
      onChange={(e) => setText(velka ? e.target.value.toUpperCase() : e.target.value)}
      onBlur={() => text.trim() !== hodnota && ulozit(text)}
      onKeyDown={(e) => e.key === "Enter" && e.currentTarget.blur()}
    />
  );
}

function VyberZe<T extends { id: number }>({
  popisek,
  moznosti,
  hodnota,
  text,
  zmenit,
  zakazano = false,
}: {
  popisek: string;
  moznosti: T[];
  hodnota: number | undefined;
  text: (m: T) => string;
  zmenit: (id: number) => void;
  zakazano?: boolean;
}) {
  return (
    <label className="vycvik-vyber">
      <span className="pole-popisek">{popisek}</span>
      <select
        value={hodnota ?? ""}
        disabled={zakazano}
        onChange={(e) => zmenit(Number(e.target.value))}
      >
        {hodnota === undefined && <option value="">vyberte</option>}
        {moznosti.map((m) => (
          <option key={m.id} value={m.id}>
            {text(m)}
          </option>
        ))}
      </select>
    </label>
  );
}

/** Smazat s potvrzením; použité jde jen zneplatnit. */
function Smazat({ pouzito, smazat }: { pouzito: number; smazat: () => void }) {
  const [potvrdit, setPotvrdit] = useState(false);
  if (pouzito > 0) {
    return (
      <p className="male seda">
        Použito v {pouzito} {pouzito === 1 ? "letu" : "letech"} – smazat nejde, jen zneplatnit
        (ve starých letech zůstane).
      </p>
    );
  }
  return potvrdit ? (
    <div className="vycvik-akce">
      <span className="male">Opravdu smazat?</span>
      <Tlacitko varianta="cervene" onClick={smazat}>
        Smazat
      </Tlacitko>
      <Tlacitko varianta="obrys" onClick={() => setPotvrdit(false)}>
        Ne
      </Tlacitko>
    </div>
  ) : (
    <div className="vycvik-akce">
      <Tlacitko varianta="obrys" onClick={() => setPotvrdit(true)}>
        Smazat
      </Tlacitko>
      <span className="male seda">zatím v žádném letu</span>
    </div>
  );
}

/** Blok Přezkoušení, jak ho uvidí pilot v novém letu (typy kategorie letadla). */
function NahledPrezkouseni({ data, kategorieId }: { data: Vycvik; kategorieId: number }) {
  const typy = data.typy.filter((t) => t.platny && t.kategorie_id === kategorieId);
  if (!typy.length) {
    return (
      <p className="male text-chyby">
        Pro {nazevKategorie(data, kategorieId)} žádný typ přezkoušení – blok se v novém letu
        neukáže (a typ není povinný).
      </p>
    );
  }
  return (
    <div className="vycvik-nahled">
      <span className="nadpisek">Přezkoušení · povinné (místo úlohy)</span>
      <div className="seznam-voleb dlouhe-kody">
        {typy.map((t) => (
          <Tlacitko key={t.id} tabIndex={-1}>
            <b>{t.kod}</b> <span>{t.nazev}</span>
          </Tlacitko>
        ))}
      </div>
    </div>
  );
}

function Segmenty<T extends { id: number }>({
  moznosti,
  hodnota,
  text,
  zmenit,
}: {
  moznosti: T[];
  hodnota: number;
  text: (m: T) => string;
  zmenit: (id: number) => void;
}) {
  return (
    <div className="segmenty">
      {moznosti.map((m) => (
        <Tlacitko key={m.id} aria-pressed={m.id === hodnota} onClick={() => zmenit(m.id)}>
          {text(m)}
        </Tlacitko>
      ))}
    </div>
  );
}

// --- osnovy a úlohy ---------------------------------------------------------------------------

function Osnovy({
  data,
  zmena,
  vyber,
  setVyber,
}: {
  data: Vycvik;
  zmena: Zmena;
  vyber: Vyber | null;
  setVyber: (v: Vyber | null) => void;
}) {
  const [sbalene, setSbalene] = useState<Set<number>>(new Set());
  const ucely = ucelyUloh(data);
  const posun = (co: "osnova" | "uloha", id: number) => (smer: -1 | 1) =>
    zmena("/posun", { co, id, smer });
  return (
    <div className="vycvik-telo">
      <div className="karta vycvik-matice" aria-label="Osnovy a úlohy">
        <div className="vycvik-radek vycvik-zahlavi nadpisek">
          <span />
          <span>Osnova / úloha</span>
          <span className="vycvik-bunky">
            {ucely.map((u) => (
              <span key={u.id} className="vycvik-bunka">
                {u.nazev}
                {u.uloha_povinna && " ·"}
              </span>
            ))}
          </span>
          <span className="vycvik-vpravo">Lety</span>
          <span className="vycvik-stred">Platná</span>
        </div>
        {data.osnovy.map((o) => {
          const otevrena = !sbalene.has(o.id);
          const lety = o.ulohy.reduce((s, u) => s + u.lety, 0);
          return (
            <div key={o.id}>
              <div
                className={["vycvik-radek vycvik-skupina vycvik-polozka", !o.platny && "vycvik-neplatna",
                  vyber?.druh === "osnova" && vyber.id === o.id && "vybrana"].filter(Boolean).join(" ")}
                {...jakoTlacitko(() => setVyber({ druh: "osnova", id: o.id }))}
              >
                <button
                  type="button"
                  className="vycvik-sbalit"
                  aria-label={otevrena ? "Sbalit" : "Rozbalit"}
                  onClick={(e) => {
                    e.stopPropagation();
                    const s = new Set(sbalene);
                    if (otevrena) s.add(o.id);
                    else s.delete(o.id);
                    setSbalene(s);
                  }}
                >
                  {otevrena ? "▾" : "▸"}
                </button>
                <span className="vycvik-nazev">
                  {popisOsnovy(o)}
                  <span className="male">{nazevKategorie(data, o.kategorie_id)}</span>
                  <span className="male seda">{o.ulohy.length} úloh</span>
                </span>
                <span className="vycvik-bunky">
                  {ucely.map((u) => {
                    const n = o.ulohy.filter((x) => x.ucely.includes(u.id)).length;
                    return (
                      <span key={u.id} className="vycvik-bunka">
                        <Policko
                          ano={n > 0 && n === o.ulohy.length}
                          castecne={n > 0 && n < o.ulohy.length}
                          popis={`${o.kod}: ${u.nazev} všem úlohám`}
                          zmenit={(ano) => zmena(`/osnovy/${o.id}/ucel`, { id: u.id, ano })}
                        />
                      </span>
                    );
                  })}
                </span>
                <span className="vycvik-vpravo male">{lety || ""}</span>
                <span className="vycvik-stred">
                  <Policko
                    ano={o.platny}
                    popis={`${o.kod} platná`}
                    zmenit={(ano) => zmena(`/osnovy/${o.id}`, { platny: ano })}
                  />
                </span>
              </div>
              {otevrena &&
                o.ulohy.map((u) => (
                  <div
                    key={u.id}
                    className={["vycvik-radek vycvik-polozka", !u.platny && "vycvik-neplatna",
                      vyber?.druh === "uloha" && vyber.id === u.id && "vybrana"].filter(Boolean).join(" ")}
                    {...jakoTlacitko(() => setVyber({ druh: "uloha", id: u.id }))}
                  >
                    <Posun posunout={posun("uloha", u.id)} />
                    <span className="vycvik-nazev">
                      {popisUlohy(u, o)}
                      {nenabiziSe(u, o) && <Stitek barva="oranzovy">nenabízí se</Stitek>}
                    </span>
                    <span className="vycvik-bunky">
                      {ucely.map((uc) => (
                        <span key={uc.id} className="vycvik-bunka">
                          <Policko
                            ano={u.ucely.includes(uc.id)}
                            popis={`${o.kod}/${u.kod}: ${uc.nazev}`}
                            zmenit={(ano) => zmena(`/ulohy/${u.id}/ucel`, { id: uc.id, ano })}
                          />
                        </span>
                      ))}
                    </span>
                    <span className={u.lety ? "vycvik-vpravo male" : "vycvik-vpravo male seda"}>
                      {u.lety || "–"}
                    </span>
                    <span className="vycvik-stred">
                      <Policko
                        ano={u.platny}
                        popis={`${o.kod}/${u.kod} platná`}
                        zmenit={(ano) => zmena(`/ulohy/${u.id}`, { platny: ano })}
                      />
                    </span>
                  </div>
                ))}
            </div>
          );
        })}
        <p className="male seda vycvik-radek">
          <span />
          <span>
            Účel s tečkou má úlohu povinnou (nastavuje se v databázi). Pořadí osnov: vyberte
            osnovu a posuňte ji vpravo.
          </span>
        </p>
      </div>
      <div className="vycvik-bok">
        <UpravaOsnov data={data} zmena={zmena} vyber={vyber} setVyber={setVyber} posun={posun} />
        <NahledNovehoLetu data={data} />
      </div>
    </div>
  );
}

function UpravaOsnov({
  data,
  zmena,
  vyber,
  setVyber,
  posun,
}: {
  data: Vycvik;
  zmena: Zmena;
  vyber: Vyber | null;
  setVyber: (v: Vyber | null) => void;
  posun: (co: "osnova" | "uloha", id: number) => (smer: -1 | 1) => void;
}) {
  if (vyber?.druh === "nova-osnova") return <NovaOsnova data={data} zmena={zmena} setVyber={setVyber} />;
  if (vyber?.druh === "nova-uloha") {
    return <NovaUloha data={data} zmena={zmena} setVyber={setVyber} osnovaId={vyber.osnovaId} />;
  }
  if (vyber?.druh === "osnova") {
    const o = data.osnovy.find((x) => x.id === vyber.id);
    if (!o) return null;
    const lety = o.ulohy.reduce((s, u) => s + u.lety, 0);
    return (
      <Blok nadpis="Vybraná osnova" popis="Vybraná osnova" vpravo={<Posun posunout={posun("osnova", o.id)} />}>
        <BlokTelo>
          <div className="vycvik-dvojice">
            <PoleUlozit key={`k${o.id}${o.kod}`} popisek="Označení" hodnota={o.kod} velka
              ulozit={(kod) => zmena(`/osnovy/${o.id}`, { kod })} />
            <PoleUlozit key={`n${o.id}${o.nazev}`} popisek="Název (bez označení)" hodnota={o.nazev}
              ulozit={(nazev) => zmena(`/osnovy/${o.id}`, { nazev })} />
          </div>
          <p className="male seda">V aplikaci: {popisOsnovy(o)}</p>
          <VyberZe
            popisek="Kategorie letadla"
            moznosti={data.kategorie}
            hodnota={o.kategorie_id}
            text={(k: Kategorie) => k.nazev}
            zakazano={lety > 0}
            zmenit={(id) => zmena(`/osnovy/${o.id}`, { kategorie_id: id })}
          />
          {o.ulohy.length > 0 ? (
            <p className="male seda">Smazat jde jen osnovu bez úloh; jinak ji zneplatněte.</p>
          ) : (
            <Smazat pouzito={0} smazat={() => zmena(`/osnovy/${o.id}/smazat`, {}, () => setVyber(null))} />
          )}
        </BlokTelo>
      </Blok>
    );
  }
  if (vyber?.druh === "uloha") {
    const o = osnovaVyberu(data, vyber);
    const u = o?.ulohy.find((x) => x.id === vyber.id);
    if (!o || !u) return null;
    // do osnovy jiné kategorie jen úloha bez letů (hlídá i databáze)
    const osnovy = data.osnovy.filter((x) => !u.lety || x.kategorie_id === o.kategorie_id);
    return (
      <Blok nadpis="Vybraná úloha" popis="Vybraná úloha" vpravo={o.kod}>
        <BlokTelo>
          <div className="vycvik-dvojice">
            <PoleUlozit key={`k${u.id}${u.kod}`} popisek={`Označení (${o.kod}/…)`} hodnota={u.kod} velka
              ulozit={(kod) => zmena(`/ulohy/${u.id}`, { kod })} />
            <PoleUlozit key={`n${u.id}${u.nazev}`} popisek="Název (bez označení)" hodnota={u.nazev}
              ulozit={(nazev) => zmena(`/ulohy/${u.id}`, { nazev })} />
          </div>
          <p className="male seda">
            V aplikaci: {popisUlohy(u, o)} · štítek na pásku „{o.kod}/{u.kod}“
          </p>
          <VyberZe
            popisek="Osnova"
            moznosti={osnovy}
            hodnota={o.id}
            text={popisOsnovy}
            zmenit={(id) => zmena(`/ulohy/${u.id}`, { osnova_id: id })}
          />
          <Smazat pouzito={u.lety} smazat={() => zmena(`/ulohy/${u.id}/smazat`, {}, () => setVyber(null))} />
        </BlokTelo>
      </Blok>
    );
  }
  return (
    <Blok nadpis="Úprava" popis="Úprava">
      <BlokTelo>
        <p className="male seda">
          Klikněte na osnovu nebo úlohu. Zaškrtávátka vlevo určují, u kterého účelu letu se úloha
          nabízí; souhrnné zaškrtávátko v řádku osnovy platí pro všechny její úlohy.
        </p>
      </BlokTelo>
    </Blok>
  );
}

function NovaOsnova({
  data,
  zmena,
  setVyber,
}: {
  data: Vycvik;
  zmena: Zmena;
  setVyber: (v: Vyber | null) => void;
}) {
  const [kod, setKod] = useState("");
  const [nazev, setNazev] = useState("");
  const [kategorie, setKategorie] = useState<number>();
  return (
    <Blok nadpis="Nová osnova" popis="Nová osnova">
      <BlokTelo>
        <div className="vycvik-dvojice">
          <Pole
            popisek="Označení"
            value={kod}
            onChange={(e) => setKod(e.target.value.toUpperCase())}
            autoFocus
          />
          <Pole popisek="Název (bez označení)" value={nazev} onChange={(e) => setNazev(e.target.value)} />
        </div>
        <VyberZe popisek="Kategorie letadla" moznosti={data.kategorie} hodnota={kategorie}
          text={(k: Kategorie) => k.nazev} zmenit={setKategorie} />
        <div className="vycvik-akce">
          <Tlacitko
            varianta="modre"
            disabled={!kod.trim() || !nazev.trim() || kategorie === undefined}
            onClick={() =>
              zmena("/osnovy", { kod, nazev, kategorie_id: kategorie }, (stav) => {
                const nova = stav.osnovy.find((o) => o.kod === kod.trim());
                setVyber(nova ? { druh: "osnova", id: nova.id } : null);
              })
            }
          >
            Založit
          </Tlacitko>
          <Tlacitko varianta="obrys" onClick={() => setVyber(null)}>
            Zrušit
          </Tlacitko>
        </div>
      </BlokTelo>
    </Blok>
  );
}

function NovaUloha({
  data,
  zmena,
  setVyber,
  osnovaId,
}: {
  data: Vycvik;
  zmena: Zmena;
  setVyber: (v: Vyber | null) => void;
  osnovaId?: number;
}) {
  const [osnova, setOsnova] = useState(osnovaId);
  const [kod, setKod] = useState("");
  const [nazev, setNazev] = useState("");
  const o = data.osnovy.find((x) => x.id === osnova);
  return (
    <Blok nadpis="Nová úloha" popis="Nová úloha">
      <BlokTelo>
        <VyberZe popisek="Osnova" moznosti={data.osnovy} hodnota={osnova} text={popisOsnovy} zmenit={setOsnova} />
        <div className="vycvik-dvojice">
          <Pole popisek={o ? `Označení (${o.kod}/…)` : "Označení"} value={kod}
            onChange={(e) => setKod(e.target.value.toUpperCase())} />
          <Pole popisek="Název (bez označení)" value={nazev} onChange={(e) => setNazev(e.target.value)} />
        </div>
        <p className="male seda">Nová úloha se zatím nenabízí – zaškrtněte jí účely vlevo.</p>
        <div className="vycvik-akce">
          <Tlacitko
            varianta="modre"
            disabled={!kod.trim() || !nazev.trim() || osnova === undefined}
            onClick={() =>
              zmena("/ulohy", { osnova_id: osnova, kod, nazev }, (stav) => {
                const nova = stav.osnovy
                  .find((x) => x.id === osnova)
                  ?.ulohy.find((u) => u.kod === kod.trim());
                setVyber(nova ? { druh: "uloha", id: nova.id } : null);
              })
            }
          >
            Založit
          </Tlacitko>
          <Tlacitko varianta="obrys" onClick={() => setVyber(null)}>
            Zrušit
          </Tlacitko>
        </div>
      </BlokTelo>
    </Blok>
  );
}

/** Náhled: co uvidí pilot v novém letu podle účelu a kategorie letadla. */
function NahledNovehoLetu({ data }: { data: Vycvik }) {
  const [ucelId, setUcelId] = useState(
    data.ucely.find((u) => u.kod === "VYCVIK")?.id ?? data.ucely[0]?.id ?? 0,
  );
  const [kategorieId, setKategorieId] = useState(data.kategorie[0]?.id ?? 0);
  const ucel = data.ucely.find((u) => u.id === ucelId);
  let obsah: ReactNode;
  if (ucel?.kod === "PREZKOUSENI") {
    obsah = <NahledPrezkouseni data={data} kategorieId={kategorieId} />;
  } else {
    const osnovy = data.osnovy
      .filter((o) => o.platny && o.kategorie_id === kategorieId)
      .map((o) => [o, o.ulohy.filter((u) => u.platny && u.ucely.includes(ucelId))] as const)
      .filter(([, ulohy]) => ulohy.length > 0);
    obsah = osnovy.length ? (
      <div className="vycvik-nahled">
        <span className="nadpisek">Úloha · {ucel?.uloha_povinna ? "povinná" : "nepovinná"}</span>
        {osnovy.map(([o, ulohy]) => (
          <div key={o.id} className="vycvik-nahled">
            <span className="male tucne">{popisOsnovy(o)}</span>
            <div className="seznam-voleb">
              {ulohy.map((u) => (
                <Tlacitko key={u.id} tabIndex={-1}>
                  <b>
                    {o.kod}/{u.kod}
                  </b>{" "}
                  <span>{u.nazev}</span>
                </Tlacitko>
              ))}
            </div>
          </div>
        ))}
      </div>
    ) : (
      <p className="male text-chyby">
        Pro {ucel?.nazev.toLocaleLowerCase("cs-CZ")} na {nazevKategorie(data, kategorieId)} žádná
        úloha – blok Úloha se v novém letu neukáže.
      </p>
    );
  }
  return (
    <Blok nadpis="Náhled: nový let" popis="Náhled: nový let" vpravo="co uvidí pilot">
      <BlokTelo>
        <Segmenty moznosti={data.ucely} hodnota={ucelId} text={(u) => u.nazev} zmenit={setUcelId} />
        <Segmenty moznosti={data.kategorie} hodnota={kategorieId} text={(k) => k.nazev} zmenit={setKategorieId} />
        {obsah}
      </BlokTelo>
    </Blok>
  );
}

// --- typy přezkoušení -------------------------------------------------------------------------

function Typy({
  data,
  zmena,
  vybrany,
  setVybrany,
}: {
  data: Vycvik;
  zmena: Zmena;
  vybrany: number | "novy" | null;
  setVybrany: (v: number | "novy" | null) => void;
}) {
  const [sbalene, setSbalene] = useState<Set<number>>(new Set());
  const nazvy = new Map(data.opravneni.map((o) => [o.id, o.nazev]));
  return (
    <div className="vycvik-telo">
      <div className="karta vycvik-matice typy" aria-label="Typy přezkoušení">
        <div className="vycvik-radek vycvik-zahlavi nadpisek">
          <span />
          <span>Kategorie / typ přezkoušení</span>
          <span>Kdo smí provést (PIC)</span>
          <span className="vycvik-vpravo">Lety</span>
          <span className="vycvik-stred">Platný</span>
        </div>
        {data.kategorie.map((k) => {
          const typy = data.typy.filter((t) => t.kategorie_id === k.id);
          const otevrena = !sbalene.has(k.id);
          return (
            <div key={k.id}>
              <div className="vycvik-radek vycvik-skupina">
                <button
                  type="button"
                  className="vycvik-sbalit"
                  aria-label={otevrena ? "Sbalit" : "Rozbalit"}
                  onClick={() => {
                    const s = new Set(sbalene);
                    if (otevrena) s.add(k.id);
                    else s.delete(k.id);
                    setSbalene(s);
                  }}
                >
                  {otevrena ? "▾" : "▸"}
                </button>
                <span className="vycvik-nazev">
                  {k.nazev}
                  <span className="male seda">{typy.length} typů</span>
                </span>
                <span />
                <span className="vycvik-vpravo male">{typy.reduce((s, t) => s + t.lety, 0) || ""}</span>
                <span />
              </div>
              {otevrena &&
                typy.map((t) => (
                  <div
                    key={t.id}
                    className={["vycvik-radek vycvik-polozka", !t.platny && "vycvik-neplatna",
                      vybrany === t.id && "vybrana"].filter(Boolean).join(" ")}
                    onClick={() => setVybrany(t.id)}
                  >
                    <Posun posunout={(smer) => zmena("/posun", { co: "typ", id: t.id, smer })} />
                    <span className="vycvik-nazev">
                      <b>{t.kod}</b> {t.nazev}
                    </span>
                    <span className="vycvik-nazev male">
                      {t.opravneni.length ? (
                        t.opravneni.map((id) => nazvy.get(id)).join(", ")
                      ) : (
                        <Stitek barva="oranzovy">nikdo ho nesmí provést</Stitek>
                      )}
                      {t.platny && t.opravneni.length > 0 && !examinatori(data, t).length && (
                        <Stitek barva="oranzovy">bez examinátora</Stitek>
                      )}
                    </span>
                    <span className={t.lety ? "vycvik-vpravo male" : "vycvik-vpravo male seda"}>
                      {t.lety || "–"}
                    </span>
                    <span className="vycvik-stred">
                      <Policko
                        ano={t.platny}
                        popis={`${t.kod} platný`}
                        zmenit={(ano) => zmena(`/typy/${t.id}`, { platny: ano })}
                      />
                    </span>
                  </div>
                ))}
            </div>
          );
        })}
      </div>
      <div className="vycvik-bok">
        {vybrany === "novy" ? (
          <NovyTyp data={data} zmena={zmena} setVybrany={setVybrany} />
        ) : (
          <UpravaTypu data={data} zmena={zmena} typ={data.typy.find((t) => t.id === vybrany)}
            setVybrany={setVybrany} />
        )}
      </div>
    </div>
  );
}

function UpravaTypu({
  data,
  zmena,
  typ: t,
  setVybrany,
}: {
  data: Vycvik;
  zmena: Zmena;
  typ: Typ | undefined;
  setVybrany: (v: number | "novy" | null) => void;
}) {
  if (!t) {
    return (
      <Blok nadpis="Úprava" popis="Úprava">
        <BlokTelo>
          <p className="male seda">
            Klikněte na typ přezkoušení. Vpravo pak zaškrtnete, kdo ho smí provést – podle toho se
            v novém letu nabízí examinátor.
          </p>
        </BlokTelo>
      </Blok>
    );
  }
  const opravneni = data.opravneni.filter((o) => o.kategorie.includes(t.kategorie_id));
  const osoby = examinatori(data, t);
  return (
    <>
      <Blok nadpis="Vybraný typ" popis="Vybraný typ" vpravo={nazevKategorie(data, t.kategorie_id)}>
        <BlokTelo>
          <div className="vycvik-dvojice">
            <PoleUlozit key={`k${t.id}${t.kod}`} popisek="Kód (označení)" hodnota={t.kod} velka
              ulozit={(kod) => zmena(`/typy/${t.id}`, { kod })} />
            <PoleUlozit key={`n${t.id}${t.nazev}`} popisek="Název (bez kódu)" hodnota={t.nazev}
              ulozit={(nazev) => zmena(`/typy/${t.id}`, { nazev })} />
          </div>
          <p className="male seda">
            V aplikaci: {t.kod} {t.nazev} · štítek na pásku „{t.kod}“
          </p>
          <VyberZe
            popisek="Kategorie letadla"
            moznosti={data.kategorie}
            hodnota={t.kategorie_id}
            text={(k: Kategorie) => k.nazev}
            zakazano={t.lety > 0}
            zmenit={(id) => zmena(`/typy/${t.id}`, { kategorie_id: id })}
          />
          <span className="nadpisek">Kdo smí provést</span>
          <Zaskrtavatka>
            {opravneni.map((o) => (
              <Zaskrtavatko
                key={o.id}
                popisek={o.nazev}
                zaskrtnuto={t.opravneni.includes(o.id)}
                zmenit={(ano) => zmena(`/typy/${t.id}/opravneni`, { id: o.id, ano })}
              />
            ))}
          </Zaskrtavatka>
          <p className="male seda">Jen oprávnění, která se pro kategorii typu vydávají.</p>
          <Smazat pouzito={t.lety} smazat={() => zmena(`/typy/${t.id}/smazat`, {}, () => setVybrany(null))} />
        </BlokTelo>
      </Blok>
      <Blok nadpis="Náhled: examinátor" popis="Náhled: examinátor" vpravo="rychlá volba v novém letu">
        <BlokTelo>
          {osoby.length ? (
            <div className="cipy">
              {osoby.map((e) => (
                <Tlacitko key={e.osoba_id} tabIndex={-1}>
                  {e.jmeno} {e.prijmeni}
                </Tlacitko>
              ))}
            </div>
          ) : (
            <p className="male text-chyby">
              {t.opravneni.length
                ? "Nikdo nemá potřebné oprávnění pro tuto kategorii – examinátora najde pilot " +
                  "jen přes Hledat…; doplňte oprávnění v detailu osoby."
                : "Typ nemá žádné oprávnění – jako examinátor se nenabídne nikdo."}
            </p>
          )}
        </BlokTelo>
      </Blok>
      <Blok nadpis="Náhled: nový let" popis="Náhled: nový let" vpravo="blok Přezkoušení">
        <BlokTelo>
          <NahledPrezkouseni data={data} kategorieId={t.kategorie_id} />
        </BlokTelo>
      </Blok>
    </>
  );
}

function NovyTyp({
  data,
  zmena,
  setVybrany,
}: {
  data: Vycvik;
  zmena: Zmena;
  setVybrany: (v: number | "novy" | null) => void;
}) {
  const [kod, setKod] = useState("");
  const [nazev, setNazev] = useState("");
  const [kategorie, setKategorie] = useState<number>();
  return (
    <Blok nadpis="Nový typ přezkoušení" popis="Nový typ přezkoušení">
      <BlokTelo>
        <div className="vycvik-dvojice">
          <Pole
            popisek="Kód (např. PC-SEP)"
            value={kod}
            onChange={(e) => setKod(e.target.value.toUpperCase())}
            autoFocus
          />
          <Pole popisek="Název (bez kódu)" value={nazev} onChange={(e) => setNazev(e.target.value)} />
        </div>
        <VyberZe popisek="Kategorie letadla" moznosti={data.kategorie} hodnota={kategorie}
          text={(k: Kategorie) => k.nazev} zmenit={setKategorie} />
        <div className="vycvik-akce">
          <Tlacitko
            varianta="modre"
            disabled={!kod.trim() || !nazev.trim() || kategorie === undefined}
            onClick={() =>
              zmena("/typy", { kod, nazev, kategorie_id: kategorie }, (stav) =>
                setVybrany(stav.typy.find((t) => t.kod === kod.trim())?.id ?? null),
              )
            }
          >
            Založit
          </Tlacitko>
          <Tlacitko varianta="obrys" onClick={() => setVybrany(null)}>
            Zrušit
          </Tlacitko>
        </div>
      </BlokTelo>
    </Blok>
  );
}
