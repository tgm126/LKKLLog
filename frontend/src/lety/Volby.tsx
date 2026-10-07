import { useState, type ReactNode } from "react";

import { Pole } from "../komponenty/Pole";
import { Tlacitko } from "../komponenty/Tlacitko";
import { proHledani } from "../text";
import type { Osoba, Uloha } from "./api";
import "../komponenty/Volby.css";
import "./Volby.css";

// Volby sdílené průvodcem a detailem letu (maketa docs/navrhy/pruvodce-mobil-v4.html):
// osoba (čipy + Hledat…), úloha (osnova, pak seznam úloh), počet.

/** Popisek PIC podle účelu (kdo je velitel letadla). */
export const PIC_NAZEV: Record<string, string> = {
  VYCVIK: "Instruktor (PIC)",
  VYCVIK_SOLO: "Žák (PIC)",
  PREZKOUSENI: "Examinátor (PIC)",
};

export const jmeno = (o: Osoba) => `${o.jmeno} ${o.prijmeni}`;

// --- kdo se nabízí: podle oprávnění osob a jejich kategorií (db/024) ------------------------

/** Role v letu: účel (null = vlečný let) a funkce osoby na letadle dané kategorie. */
type Hledana = { ucel: string | null; funkce: string; kategorie: string | undefined };

/** Smí osoba zastat roli (letadlo ještě nevybrané = na čemkoli)? */
const smi = (o: Osoba, h: Hledana) =>
  o.role.some(
    (r) =>
      r.ucel === h.ucel &&
      r.funkce === h.funkce &&
      (h.kategorie === undefined || r.kategorie === h.kategorie),
  );

/** Rychlá volba osoby: kdo smí roli zastat podle oprávnění; když nikdo, záloha (Já,
 *  naposledy létající). Ostatní najde „Hledat…“. */
export function rychlaVolba(osoby: Osoba[], hledana: Hledana, zaloha: number[]): number[] {
  const smiji = osoby.filter((o) => smi(o, hledana)).map((o) => o.id);
  return smiji.length > 0 ? smiji : zaloha;
}

/** Osoba: rychlá volba (Já, nedávní…) a „Hledat…“ (hledání podle jména ve všech osobách).
 *  Po výběru zůstane jen vybraná osoba (plně modře) a „Hledat…“, ostatní se skryjí; ťuknutím
 *  na vybranou se nabídka znovu otevře. Vyloučené osoby (už mají jinou funkci) se nenabízejí. */
export function VolbaOsoby({
  osoby,
  jaId,
  rychle,
  vybrana,
  vyloucit = [],
  vybrat,
  pred,
  menit = false,
}: {
  osoby: Osoba[];
  jaId: number;
  rychle: number[];
  vybrana: number | undefined;
  vyloucit?: (number | undefined)[];
  vybrat: (id: number) => void;
  /** Volba před osobami (Aeroklub u plátce). */
  pred?: ReactNode;
  /** Rovnou celá rychlá volba i s vybranou osobou (úprava v detailu letu). */
  menit?: boolean;
}) {
  const [hledam, setHledam] = useState(false);
  const [text, setText] = useState("");
  const [otevrena, setOtevrena] = useState(menit);
  const vybranaOsoba = osoby.find((o) => o.id === vybrana);
  const popis = (o: Osoba) => (o.id === jaId ? `Já (${jmeno(o)})` : jmeno(o));
  const hledat = proHledani(text.trim());
  const nabidka = (
    hledam
      ? osoby.filter((o) => proHledani(jmeno(o)).includes(hledat))
      : [...new Set([...rychle, ...(vybrana ? [vybrana] : [])])]
          .map((id) => osoby.find((o) => o.id === id))
          .filter((o): o is Osoba => o !== undefined)
  )
    .filter((o) => !vyloucit.includes(o.id))
    .sort((a, b) => Number(b.id === jaId) - Number(a.id === jaId));
  return (
    <>
      {hledam && (
        <Pole
          popisek="Hledat osobu"
          value={text}
          onChange={(e) => setText(e.target.value)}
          autoFocus
        />
      )}
      <div className="cipy">
        {!hledam && !otevrena && vybranaOsoba ? (
          <Tlacitko aria-pressed onClick={() => setOtevrena(true)}>
            {popis(vybranaOsoba)}
          </Tlacitko>
        ) : (
          <>
            {pred}
            {nabidka.map((o) => (
              <Tlacitko
                key={o.id}
                aria-pressed={o.id === vybrana}
                onClick={() => {
                  // po výběru zůstane jen vybraná osoba a Hledat…
                  setHledam(false);
                  setText("");
                  setOtevrena(false);
                  vybrat(o.id);
                }}
              >
                {popis(o)}
              </Tlacitko>
            ))}
          </>
        )}
        {!hledam && (
          <Tlacitko className="hledat" onClick={() => setHledam(true)}>
            Hledat…
          </Tlacitko>
        )}
      </div>
    </>
  );
}

/** Úloha ve dvou krocích: osnova (IU, IA, II…), pak seznam úloh v ní („kód · název“).
 *  Co je vybrané, zůstane samo (ostatní se skryjí); ťuknutím na vybrané se nabídka znovu
 *  otevře. Je-li úloha povinná a osnova jen jedna, je rovnou otevřená. Nepovinnou úlohu jde
 *  zrušit volbou „Bez úlohy“. */
export function VolbaUlohy({
  ulohy,
  povinna,
  vybrana,
  vybrat,
  menit = false,
}: {
  ulohy: Uloha[];
  povinna: boolean;
  vybrana: Uloha | undefined;
  vybrat: (id: number | undefined) => void;
  /** Rovnou nabídka úloh vybrané osnovy (úprava v detailu letu). */
  menit?: boolean;
}) {
  const osnovy = [...new Map(ulohy.map((u) => [u.osnova_id, u.osnova])).entries()];
  const [osnovaId, setOsnovaId] = useState<number | undefined>(
    vybrana?.osnova_id ?? (povinna && osnovy.length === 1 ? osnovy[0]![0] : undefined),
  );
  // Která nabídka je otevřená: výběr osnovy, výběr úlohy v osnově, nebo žádná (vybráno).
  const [otevreno, setOtevreno] = useState<"osnova" | "uloha" | null>(
    vybrana && !menit ? null : osnovaId === undefined ? "osnova" : "uloha",
  );
  const osnova = osnovy.find(([id]) => id === osnovaId);
  const vybrat_ = (id: number | undefined) => {
    vybrat(id);
    setOtevreno(null);
  };
  const radek = (u: Uloha, onClick: () => void) => {
    const [kod, ...nazev] = u.nazev.split(" ");
    return (
      <Tlacitko key={u.id} aria-pressed={u.id === vybrana?.id} onClick={onClick}>
        <b>{kod}</b> <span>{nazev.join(" ")}</span>
      </Tlacitko>
    );
  };
  const vOsnove = otevreno === "uloha" || !vybrana || vybrana.osnova_id !== osnovaId;
  return (
    <>
      <div className="cipy">
        {otevreno === "osnova" || !osnova ? (
          osnovy.map(([id, nazev]) => (
            <Tlacitko
              key={id}
              aria-pressed={id === osnovaId}
              onClick={() => {
                setOsnovaId(id);
                setOtevreno("uloha");
              }}
            >
              {nazev}
            </Tlacitko>
          ))
        ) : (
          <Tlacitko aria-pressed onClick={() => setOtevreno("osnova")}>
            {osnova[1]}
          </Tlacitko>
        )}
      </div>
      {osnova && otevreno !== "osnova" && (
        <div className="seznam-voleb">
          {vOsnove ? (
            <>
              {ulohy.filter((u) => u.osnova_id === osnovaId).map((u) => radek(u, () => vybrat_(u.id)))}
              {!povinna && vybrana && (
                <Tlacitko onClick={() => vybrat_(undefined)}>
                  <span />
                  <span>Bez úlohy</span>
                </Tlacitko>
              )}
            </>
          ) : (
            radek(vybrana, () => setOtevreno("uloha"))
          )}
        </div>
      )}
    </>
  );
}

/** Řada tlačítek 1 … počet (POB, přistání celkem). */
export function VolbaPoctu({
  pocet,
  vybrano,
  vybrat,
}: {
  pocet: number;
  vybrano: number | null;
  vybrat: (n: number) => void;
}) {
  return (
    <div className="volby-pocet">
      {Array.from({ length: pocet }, (_, k) => k + 1).map((n) => (
        <Tlacitko
          key={n}
          className="cisla"
          aria-pressed={n === vybrano}
          onClick={() => vybrat(n)}
        >
          {n}
        </Tlacitko>
      ))}
    </div>
  );
}
