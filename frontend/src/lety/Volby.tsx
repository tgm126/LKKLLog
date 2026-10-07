import { useState, type ReactNode } from "react";

import { Pole } from "../komponenty/Pole";
import { Tlacitko } from "../komponenty/Tlacitko";
import type { Osoba, Uloha } from "./api";
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

/** Bez diakritiky a malými (hledání „cacky“ najde „Čacký“). */
const proHledani = (text: string) =>
  text.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLocaleLowerCase("cs-CZ");

/** Osoba: rychlá volba (Já, nedávní…), vybraná plně modře s ✓; „Hledat…“ otevře hledání
 *  podle jména ve všech osobách. Vyloučené osoby (už mají jinou funkci) se nenabízejí. */
export function VolbaOsoby({
  osoby,
  jaId,
  rychle,
  vybrana,
  vyloucit = [],
  vybrat,
  pred,
}: {
  osoby: Osoba[];
  jaId: number;
  rychle: number[];
  vybrana: number | undefined;
  vyloucit?: (number | undefined)[];
  vybrat: (id: number) => void;
  /** Volba před osobami (Aeroklub u plátce). */
  pred?: ReactNode;
}) {
  const [hledam, setHledam] = useState(false);
  const [text, setText] = useState("");
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
        {pred}
        {nabidka.map((o) => (
          <Tlacitko
            key={o.id}
            varianta="obrys"
            aria-pressed={o.id === vybrana}
            onClick={() => {
              // po výběru z hledání zpět na rychlou volbu (vybraná osoba + Hledat…)
              setHledam(false);
              setText("");
              vybrat(o.id);
            }}
          >
            {o.id === jaId ? `Já (${jmeno(o)})` : jmeno(o)}
          </Tlacitko>
        ))}
        {!hledam && (
          <Tlacitko varianta="obrys" className="hledat" onClick={() => setHledam(true)}>
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
      <Tlacitko key={u.id} varianta="obrys" aria-pressed={u.id === vybrana?.id} onClick={onClick}>
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
              varianta="obrys"
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
          <Tlacitko varianta="obrys" aria-pressed onClick={() => setOtevreno("osnova")}>
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
                <Tlacitko varianta="obrys" onClick={() => vybrat_(undefined)}>
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
          varianta="obrys"
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
