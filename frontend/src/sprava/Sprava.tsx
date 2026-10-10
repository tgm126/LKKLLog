import { useState } from "react";

import { denSlovy } from "../cas";
import { Dialog } from "../komponenty/Dialog";
import { Hlaska } from "../komponenty/Hlaska";
import { Kalendar } from "../komponenty/Kalendar";
import { Blok, Obrazovka, useZpet } from "../komponenty/Obrazovka";
import { Oznameni, useOznamit } from "../komponenty/Oznameni";
import { Tlacitko } from "../komponenty/Tlacitko";
import { Zaskrtavatka, Zaskrtavatko } from "../komponenty/Zaskrtavatko";
import { useDnySLety, useNastaveniSystemu, useSmazatDen, useZmenitNastaveni, type DenSLety } from "./api";
import { pocetLetu } from "../text";
import "../komponenty/Oznameni.css";

// Správa systému – jen admin, z nabídky uživatele (docs/modul-sprava.md): smazání letů
// celého dne v kalendáři a nastavení systému.

export function SmazatLetyDne() {
  const zpet = useZpet();
  const { data, error } = useDnySLety();
  return (
    <Obrazovka zpet={zpet} zpetPopis="Zpět" nadpis="Smazat lety dne">
      {error && <Hlaska>{error.message}</Hlaska>}
      {data && <SmazatVKalendari dny={data} />}
      <div className="oznameni-dole">
        <Oznameni />
      </div>
    </Obrazovka>
  );
}

/** Kalendář letů, klik na den s lety = potvrzení smazání. */
function SmazatVKalendari({ dny }: { dny: DenSLety[] }) {
  const lety = new Map(dny.map((d) => [d.den, d.lety]));
  const [vybrany, setVybrany] = useState<string | null>(null);
  const smazat = useSmazatDen();
  const oznamit = useOznamit();
  const pocet = vybrany ? (lety.get(vybrany) ?? 0) : 0;

  return (
    <>
      <Kalendar dny={dny} vybrat={setVybrany} />
      <p className="male seda">
        Den letu je datum vzletu, u letu, který nevzlétl, datum založení (UTC). Smazání nejde vrátit; v historii zůstane
        záznam, kdo a kdy lety smazal.
      </p>
      {vybrany && (
        <Dialog nadpis={`Smazat lety ${denSlovy(vybrany).toLocaleLowerCase("cs-CZ")}?`} zavrit={() => setVybrany(null)}>
          <p>
            Smaže se <b>{pocetLetu(pocet)}</b> ve všech stavech (i ve vzduchu a naplánované) s posádkou a T&G, u vleku obě
            poloviny. Nejde to vrátit.
          </p>
          <Tlacitko
            varianta="cervene"
            hlavni
            disabled={smazat.isPending}
            onClick={() =>
              smazat.mutate(vybrany, {
                onSuccess: (r) => {
                  oznamit({
                    text: `Smazáno ${pocetLetu(r.smazano)} – ${denSlovy(r.den)}`,
                  });
                  setVybrany(null);
                },
              })
            }
          >
            Smazat {pocetLetu(pocet)}
          </Tlacitko>
          <Tlacitko varianta="obrys" onClick={() => setVybrany(null)}>
            Zpět
          </Tlacitko>
        </Dialog>
      )}
    </>
  );
}

export function NastaveniSystemu() {
  const zpet = useZpet();
  const { data, error } = useNastaveniSystemu();
  const zmenit = useZmenitNastaveni();
  return (
    <Obrazovka zpet={zpet} zpetPopis="Zpět" nadpis="Nastavení">
      {error && <Hlaska>{error.message}</Hlaska>}
      {data && (
        <Blok nadpis="Provoz">
          <Zaskrtavatka>
            <Zaskrtavatko
              popisek="Testovací provoz"
              pod="žlutý pruh nahoře u všech"
              zaskrtnuto={data.testovaci_provoz}
              zakazano={zmenit.isPending}
              zmenit={(testovaci_provoz) => zmenit.mutate({ testovaci_provoz })}
            />
          </Zaskrtavatka>
        </Blok>
      )}
    </Obrazovka>
  );
}
