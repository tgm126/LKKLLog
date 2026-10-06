import { useState } from "react";

import { Pole } from "../komponenty/Pole";
import { Tlacitko } from "../komponenty/Tlacitko";
import type { Nabidky } from "./api";
import "./Volby.css";

/** Místo: letiště, nebo popis místa v terénu; prázdné = domovské letiště. */
export type Misto = { id: number | null; popis: string | null };

/** Název místa pro údaj „Místo vzletu / přistání“ (prázdné = domovské letiště). */
export function nazevMista(nabidky: Nabidky, misto: Misto | undefined) {
  if (misto?.popis) return misto.popis;
  const letiste = nabidky.letiste.find((l) => (misto?.id ? l.id === misto.id : l.domovske));
  return letiste ? `${letiste.kod} ${letiste.nazev}` : null;
}

/** Letiště (hledání podle kódu nebo názvu) nebo jiné místo popisem (přistání do terénu). */
export function VyberMista({
  nabidky,
  ulozit,
}: {
  nabidky: Nabidky;
  ulozit: (id: number | null, popis: string | null) => void;
}) {
  const [hledat, setHledat] = useState("");
  const [popis, setPopis] = useState("");
  const h = hledat.trim().toLocaleLowerCase("cs-CZ");
  const letiste = [...nabidky.letiste]
    .sort((a, b) => Number(b.domovske) - Number(a.domovske))
    .filter((x) => !h || `${x.kod} ${x.nazev}`.toLocaleLowerCase("cs-CZ").includes(h))
    .slice(0, 12);
  return (
    <>
      <Pole
        popisek="Hledat letiště (kód nebo název)"
        value={hledat}
        onChange={(e) => setHledat(e.target.value)}
        autoCapitalize="characters"
      />
      <div className="cipy">
        {letiste.map((x) => (
          <Tlacitko key={x.id} varianta="obrys" onClick={() => ulozit(x.id, null)}>
            {x.kod} {x.nazev}
          </Tlacitko>
        ))}
      </div>
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
