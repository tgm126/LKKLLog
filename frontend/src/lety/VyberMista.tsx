import { useState } from "react";

import { Pole } from "../komponenty/Pole";
import { Tlacitko } from "../komponenty/Tlacitko";
import { useMujProvoz } from "../provoz/api";
import { proHledani } from "../text";
import type { Nabidky } from "./api";
import "../komponenty/Volby.css";

/** Místo: letiště, nebo popis místa v terénu; prázdné = moje letiště (můj provoz). */
export type Misto = { id: number | null; popis: string | null };

/** Název místa pro údaj „Místo vzletu / přistání“ (prázdné = moje letiště). */
export function nazevMista(nabidky: Nabidky, misto: Misto | undefined, mojeId: number | undefined) {
  if (misto?.popis) return misto.popis;
  const letiste = nabidky.letiste.find((l) => l.id === (misto?.id ?? mojeId));
  return letiste ? `${letiste.kod} ${letiste.nazev}` : null;
}

/** Moje letiště na dnešek (můj provoz, jinak domovské). */
export function useMojeLetisteId(): number | undefined {
  return useMujProvoz().data?.letiste?.id;
}

/** Letiště ťuknutím: rychlá volba (příznak v číselníku) a moje letiště (první); ostatní přes
 *  „Hledat…“ podle kódu nebo názvu (bez diakritiky). */
export function VolbaLetiste({
  letiste,
  vybrane,
  vybrat,
}: {
  letiste: Nabidky["letiste"];
  /** Vybrané letiště (zvýrazněné a vždy nabízené); bez něj se nic nezvýrazní. */
  vybrane?: number;
  vybrat: (id: number) => void;
}) {
  const [hledam, setHledam] = useState(false);
  const [hledat, setHledat] = useState("");
  const mojeId = useMojeLetisteId();
  const h = proHledani(hledat.trim());
  const nabidka = (
    hledam
      ? letiste.filter((l) => !h || proHledani(`${l.kod} ${l.nazev}`).includes(h)).slice(0, 12)
      : letiste.filter((l) => l.rychla_volba || l.id === mojeId || l.id === vybrane)
  ).sort((a, b) => Number(b.id === mojeId) - Number(a.id === mojeId));
  return (
    <>
      {hledam && (
        <Pole
          popisek="Hledat letiště (kód nebo název)"
          value={hledat}
          onChange={(e) => setHledat(e.target.value)}
          autoCapitalize="characters"
          autoFocus
        />
      )}
      <div className="cipy">
        {nabidka.map((l) => (
          <Tlacitko
            key={l.id}
            aria-pressed={vybrane === undefined ? undefined : l.id === vybrane}
            onClick={() => vybrat(l.id)}
          >
            {l.kod} {l.nazev}
          </Tlacitko>
        ))}
        {!hledam && (
          <Tlacitko className="hledat" onClick={() => setHledam(true)}>
            Hledat…
          </Tlacitko>
        )}
      </div>
    </>
  );
}

/** Místo: letiště (rychlá volba, ostatní přes Hledat…) nebo jiné místo popisem (přistání
 *  do terénu). */
export function VyberMista({
  nabidky,
  ulozit,
}: {
  nabidky: Nabidky;
  ulozit: (id: number | null, popis: string | null) => void;
}) {
  const [popis, setPopis] = useState("");
  return (
    <>
      <VolbaLetiste letiste={nabidky.letiste} vybrat={(id) => ulozit(id, null)} />
      <Pole
        popisek="Jiné místo (přistání do terénu)"
        value={popis}
        onChange={(e) => setPopis(e.target.value)}
      />
      <Tlacitko varianta="obrys" disabled={!popis.trim()} onClick={() => ulozit(null, popis.trim())}>
        Uložit místo
      </Tlacitko>
    </>
  );
}
