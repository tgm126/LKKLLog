import { useState } from "react";

import { denSlovy, ted } from "../cas";
import { Dialog } from "../komponenty/Dialog";
import { Hlaska } from "../komponenty/Hlaska";
import { Blok, BlokTelo, Obrazovka, useZpet } from "../komponenty/Obrazovka";
import { Oznameni, useOznamit } from "../komponenty/Oznameni";
import { Tlacitko } from "../komponenty/Tlacitko";
import { Zaskrtavatka, Zaskrtavatko } from "../komponenty/Zaskrtavatko";
import { useDnySLety, useNastaveniSystemu, useSmazatDen, useZmenitNastaveni, type DenSLety } from "./api";
import "../komponenty/Oznameni.css";
import "./Sprava.css";

// Správa systému – jen admin, z nabídky uživatele (docs/modul-sprava.md): smazání letů
// celého dne v kalendáři a nastavení systému.

const DNY_TYDNE = ["Po", "Út", "St", "Čt", "Pá", "So", "Ne"];

/** „1 let“, „3 lety“, „44 letů“ */
const letu = (n: number) => `${n} ${n === 1 ? "let" : n >= 2 && n <= 4 ? "lety" : "letů"}`;

/** Měsíc RRRR-MM posunutý o `o` měsíců. */
function posunMesice(mesic: string, o: number): string {
  const d = new Date(`${mesic}-01T12:00:00Z`);
  d.setUTCMonth(d.getUTCMonth() + o);
  return d.toISOString().slice(0, 7);
}

export function SmazatLetyDne() {
  const zpet = useZpet();
  const { data, error } = useDnySLety();
  return (
    <Obrazovka zpet={zpet} zpetPopis="Zpět" nadpis="Smazat lety dne">
      {error && <Hlaska>{error.message}</Hlaska>}
      {data && <Kalendar dny={data} />}
      <div className="oznameni-dole">
        <Oznameni />
      </div>
    </Obrazovka>
  );
}

/** Kalendář po měsících: dny s lety tučně s počtem letů, klik = potvrzení smazání. */
function Kalendar({ dny }: { dny: DenSLety[] }) {
  const dnes = ted().toISOString().slice(0, 10);
  const lety = new Map(dny.map((d) => [d.den, d.lety]));
  const [mesic, setMesic] = useState((dny.at(-1)?.den ?? dnes).slice(0, 7));
  const [vybrany, setVybrany] = useState<string | null>(null);
  const smazat = useSmazatDen();
  const oznamit = useOznamit();

  const prvni = new Date(`${mesic}-01T12:00:00Z`);
  const posun = (prvni.getUTCDay() + 6) % 7; // týden od pondělí
  const pocetDni = new Date(Date.UTC(prvni.getUTCFullYear(), prvni.getUTCMonth() + 1, 0)).getUTCDate();
  const nazev = prvni.toLocaleDateString("cs-CZ", {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
  const dnyMesice = Array.from({ length: pocetDni }, (_, i) => `${mesic}-${String(i + 1).padStart(2, "0")}`);
  const pocet = vybrany ? (lety.get(vybrany) ?? 0) : 0;

  return (
    <>
      <Blok nadpis="Kalendář letů" vpravo="tučně = dny s lety" popis="Kalendář letů">
        <BlokTelo>
          <div className="kalendar-mesic">
            <Tlacitko varianta="bez-ramu" aria-label="Předchozí měsíc" onClick={() => setMesic(posunMesice(mesic, -1))}>
              ‹
            </Tlacitko>
            <span className="velke tucne">{nazev}</span>
            <Tlacitko varianta="bez-ramu" aria-label="Další měsíc" onClick={() => setMesic(posunMesice(mesic, 1))}>
              ›
            </Tlacitko>
          </div>
          <div className="kalendar">
            {DNY_TYDNE.map((d) => (
              <span key={d} className="kalendar-den-tydne male seda">
                {d}
              </span>
            ))}
            {Array.from({ length: posun }, (_, i) => (
              <span key={`prazdny-${i}`} />
            ))}
            {dnyMesice.map((den) => {
              const n = lety.get(den);
              return (
                <button
                  key={den}
                  type="button"
                  className={["kalendar-den", n && "s-lety", den === dnes && "dnes"].filter(Boolean).join(" ")}
                  disabled={!n}
                  aria-label={n ? `${denSlovy(den)} – ${letu(n)}` : denSlovy(den)}
                  onClick={() => setVybrany(den)}
                >
                  <span className="cisla">{Number(den.slice(8))}</span>
                  <span className="kalendar-pocet male cisla">{n ?? "\u00a0"}</span>
                </button>
              );
            })}
          </div>
        </BlokTelo>
      </Blok>
      <p className="male seda">
        Den letu je datum vzletu, u letu, který nevzlétl, datum založení (UTC). Smazání nejde vrátit; v historii zůstane
        záznam, kdo a kdy lety smazal.
      </p>
      {vybrany && (
        <Dialog nadpis={`Smazat lety ${denSlovy(vybrany).toLocaleLowerCase("cs-CZ")}?`} zavrit={() => setVybrany(null)}>
          <p>
            Smaže se <b>{letu(pocet)}</b> ve všech stavech (i ve vzduchu a naplánované) s posádkou a T&G, u vleku obě
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
                    text: `Smazáno ${letu(r.smazano)} – ${denSlovy(r.den)}`,
                  });
                  setVybrany(null);
                },
              })
            }
          >
            Smazat {letu(pocet)}
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
