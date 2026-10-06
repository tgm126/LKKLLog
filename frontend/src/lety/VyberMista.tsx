import { useState } from "react";

import { Pole } from "../komponenty/Pole";
import { Tlacitko } from "../komponenty/Tlacitko";
import type { Nabidky } from "./api";
import "./Volby.css";

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
      <div className="navrhy">
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


/** Místo: letiště, nebo popis místa v terénu; prázdné = domovské letiště. */
export type Misto = { id: number | null; popis: string | null };

/** Volba místa v průvodci: vybrané místo modře (výchozí domovské letiště), „Jiné…“ otevře
 *  hledání letiště nebo popis místa. */
export function VolbaMista({
  nabidky,
  misto,
  zmenit,
}: {
  nabidky: Nabidky;
  misto: Misto | undefined;
  zmenit: (misto: Misto | undefined) => void;
}) {
  const [hledam, setHledam] = useState(false);
  const domovske = nabidky.letiste.find((l) => l.domovske);
  const letiste = nabidky.letiste.find((l) => l.id === (misto?.id ?? domovske?.id));
  const nazev = misto?.popis ?? (letiste ? `${letiste.kod} ${letiste.nazev}` : "—");
  if (hledam) {
    return (
      <VyberMista
        nabidky={nabidky}
        ulozit={(id, popis) => {
          zmenit(id === domovske?.id ? undefined : { id, popis });
          setHledam(false);
        }}
      />
    );
  }
  return (
    <div className="navrhy">
      <Tlacitko varianta="obrys" aria-pressed onClick={() => setHledam(true)}>
        {nazev}
      </Tlacitko>
      <Tlacitko varianta="bez-ramu" onClick={() => setHledam(true)}>
        Jiné…
      </Tlacitko>
    </div>
  );
}
