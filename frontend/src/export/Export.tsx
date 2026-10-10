import { useState } from "react";

import { denSlovy, ted } from "../cas";
import { Dialog } from "../komponenty/Dialog";
import { Hlaska } from "../komponenty/Hlaska";
import { Kalendar, nazevMesice, posunMesice } from "../komponenty/Kalendar";
import { Blok, BlokTelo, Obrazovka, useZpet } from "../komponenty/Obrazovka";
import { Oznameni } from "../komponenty/Oznameni";
import { Tlacitko } from "../komponenty/Tlacitko";
import { pocetLetu } from "../text";
import { useExportovat, useNabidkaExportu, type ExportIn, type NabidkaExportu } from "./api";
import "../komponenty/Oznameni.css";
import "../komponenty/Volby.css";

// Export letů (docs/modul-export.md): den v kalendáři nebo měsíc ze seznamu, po potvrzení
// přijde PDF ukončených letů e-mailem adminům.

export function ExportLetu() {
  const zpet = useZpet();
  const { data, error } = useNabidkaExportu();
  return (
    <Obrazovka zpet={zpet} zpetPopis="Zpět" nadpis="Export letů">
      {error && <Hlaska>{error.message}</Hlaska>}
      {data && <Vyber nabidka={data} />}
      <div className="oznameni-dole">
        <Oznameni />
      </div>
    </Obrazovka>
  );
}

type Vybrane = ExportIn & { nazev: string; lety: number };

function Vyber({ nabidka }: { nabidka: NabidkaExportu }) {
  const [druh, setDruh] = useState<ExportIn["druh"]>("DEN");
  const [vybrane, setVybrane] = useState<Vybrane | null>(null);
  const exportovat = useExportovat();
  const lety = new Map(nabidka.dny.map((d) => [d.den, d.lety]));
  const adresy = nabidka.adresy.join(", ");

  const tentoMesic = ted().toISOString().slice(0, 7);
  const mesice = Array.from({ length: 12 }, (_, i) => {
    const mesic = posunMesice(tentoMesic, -i);
    const n = nabidka.dny.filter((d) => d.den.startsWith(mesic)).reduce((s, d) => s + d.lety, 0);
    return { mesic, lety: n };
  });

  return (
    <>
      <div className="segmenty">
        <Tlacitko aria-pressed={druh === "DEN"} onClick={() => setDruh("DEN")}>
          Den
        </Tlacitko>
        <Tlacitko aria-pressed={druh === "MESIC"} onClick={() => setDruh("MESIC")}>
          Měsíc
        </Tlacitko>
      </div>
      {druh === "DEN" ? (
        <Kalendar
          dny={nabidka.dny}
          vybrat={(den) => setVybrane({ druh, den, nazev: denSlovy(den).toLocaleLowerCase("cs-CZ"), lety: lety.get(den) ?? 0 })}
        />
      ) : (
        <Blok nadpis="Posledních 12 měsíců" popis="Měsíce">
          <BlokTelo>
            <div className="cipy">
              {mesice.map((m) => (
                <Tlacitko
                  key={m.mesic}
                  disabled={!m.lety}
                  onClick={() => setVybrane({ druh, den: `${m.mesic}-01`, nazev: nazevMesice(m.mesic), lety: m.lety })}
                >
                  {nazevMesice(m.mesic)} <span className="cisla">{m.lety}</span>
                </Tlacitko>
              ))}
            </div>
          </BlokTelo>
        </Blok>
      )}
      <p className="male seda">
        Do PDF jdou ukončené lety (časy UTC) a souhrny podle letadel a plátců; přijde e-mailem na{" "}
        {adresy || "– (žádný admin se nesmí přihlásit)"}. Den letu je datum vzletu.
      </p>
      {vybrane && (
        <Dialog nadpis={`Poslat PDF – ${vybrane.nazev}?`} zavrit={() => setVybrane(null)}>
          <p>
            {vybrane.nazev}, <b>{pocetLetu(vybrane.lety)}</b> – na {adresy}
          </p>
          <Tlacitko
            varianta="modre"
            hlavni
            disabled={exportovat.isPending}
            onClick={() =>
              exportovat.mutate({ druh: vybrane.druh, den: vybrane.den }, { onSettled: () => setVybrane(null) })
            }
          >
            Poslat
          </Tlacitko>
          <Tlacitko varianta="obrys" onClick={() => setVybrane(null)}>
            Zpět
          </Tlacitko>
        </Dialog>
      )}
    </>
  );
}
