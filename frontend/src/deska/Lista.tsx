import { NavLink, useNavigate } from "react-router";

import type { Ja } from "../api";
import { denSlovy, hodinyMinuty } from "../cas";
import { CasUtc, NabidkaUzivatele } from "../komponenty/Hlavicka";
import { Stitek } from "../komponenty/Stitek";
import { Tlacitko } from "../komponenty/Tlacitko";
import type { Den } from "../lety/api";
import { useTik } from "../tik";

// Horní lišta desky (docs/modul-desktop.md 3): název, navigace, den se šipkami, sluneční časy
// se zbývajícím časem do konce soumraku, hodiny UTC a nabídka uživatele (jako na mobilu).

/** Den o `o` dní dál (RRRR-MM-DD). */
export function posunDne(den: string, o: number): string {
  const d = new Date(`${den}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() + o);
  return d.toISOString().slice(0, 10);
}

/** „do TE 2:40“ – jen dnes a před koncem občanského soumraku. */
function DoKonceSoumraku({ te }: { te: string }) {
  const zbyva = new Date(te).getTime() - useTik().getTime();
  if (zbyva <= 0) return null;
  const min = Math.floor(zbyva / 60_000);
  return (
    <span className="do-te" title="Zbývá do konce občanského soumraku">
      do TE {Math.floor(min / 60)}:{String(min % 60).padStart(2, "0")}
    </span>
  );
}

export function Lista({
  ja,
  den,
  dnes,
  zmenitDen,
  siroka,
  souhrny,
  prepnoutSouhrny,
}: {
  ja: Ja;
  /** Zobrazený den (sluneční časy, letiště). */
  den: Den;
  /** Dnešní datum (RRRR-MM-DD) – dál než dnes listovat nejde. */
  dnes: string;
  zmenitDen: (den: string) => void;
  /** Široká deska: všechny sluneční časy, souhrny ve sloupci (jinak za tlačítkem). */
  siroka: boolean;
  souhrny: boolean;
  prepnoutSouhrny: () => void;
}) {
  const navigate = useNavigate();
  const { tb, sr, ss, te } = den.slunce;
  const casy: [string, string | null][] = siroka
    ? [["TB", tb], ["SR", sr], ["SS", ss], ["TE", te]]
    : [["SS", ss], ["TE", te]];
  const jinde = den.letiste && !den.letiste.domovske ? den.letiste : null;
  return (
    <header className="lista-desky">
      <span className="velke tucne">AK Kladno Log</span>
      <nav className="navigace-desky">
        {/* deska je vždy Provoz (i s otevřeným panelem /let/…, /novy-let) */}
        <NavLink to="/" className="active">
          Provoz
        </NavLink>
        {/* správa osob a letadel jen pro toho, kdo má právo (server ho hlídá také) */}
        {ja.prava.spravuje_osoby && <NavLink to="/osoby">Osoby</NavLink>}
        {ja.prava.spravuje_letadla && <NavLink to="/letadla">Letadla</NavLink>}
      </nav>
      {ja.jen_cteni && (
        <span title="Sdílený počítač – nic nejde změnit; pro změny se odhlaste a přihlaste znovu">
          <Stitek barva="oranzovy">Jen ke čtení</Stitek>
        </span>
      )}
      <div className="den-desky">
        <Tlacitko varianta="bez-ramu" aria-label="Předchozí den" onClick={() => zmenitDen(posunDne(den.den, -1))}>
          ‹
        </Tlacitko>
        <b>{denSlovy(den.den)}</b>
        <Tlacitko
          varianta="bez-ramu"
          aria-label="Další den"
          disabled={den.den >= dnes}
          onClick={() => zmenitDen(posunDne(den.den, 1))}
        >
          ›
        </Tlacitko>
      </div>
      {jinde && ja.jen_cteni && <Stitek barva="oranzovy">{jinde.kod}</Stitek>}
      {jinde && !ja.jen_cteni && (
        <button
          type="button"
          className="letiste-desky"
          aria-label={`Letiště pro dnešek: ${jinde.kod} ${jinde.nazev}`}
          onClick={() => navigate("/muj-provoz/letiste")}
        >
          <Stitek barva="oranzovy">{jinde.kod}</Stitek>
        </button>
      )}
      {tb && (
        <span className="slunce-desky male cisla">
          {casy.map(([zkratka, cas]) => (
            <span key={zkratka}>
              <b className="seda">{zkratka}</b> {cas && hodinyMinuty(cas)}
            </span>
          ))}
          {te && den.den === dnes && <DoKonceSoumraku te={te} />}
        </span>
      )}
      {!siroka && (
        <Tlacitko varianta="obrys" aria-pressed={souhrny} onClick={prepnoutSouhrny}>
          Souhrny
        </Tlacitko>
      )}
      <CasUtc />
      <NabidkaUzivatele ja={ja} />
    </header>
  );
}
