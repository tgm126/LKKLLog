import { useState } from "react";

import { Pole } from "../komponenty/Pole";
import { Tlacitko } from "../komponenty/Tlacitko";
import { useMujProvoz } from "../provoz/api";
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

/** Letiště (hledání podle kódu nebo názvu; moje letiště první) nebo jiné místo popisem
 *  (přistání do terénu). */
export function VyberMista({
  nabidky,
  ulozit,
}: {
  nabidky: Nabidky;
  ulozit: (id: number | null, popis: string | null) => void;
}) {
  const [hledat, setHledat] = useState("");
  const [popis, setPopis] = useState("");
  const mojeId = useMojeLetisteId();
  const h = hledat.trim().toLocaleLowerCase("cs-CZ");
  const letiste = [...nabidky.letiste]
    .sort((a, b) => Number(b.id === mojeId) - Number(a.id === mojeId))
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
          <Tlacitko key={x.id} onClick={() => ulozit(x.id, null)}>
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
