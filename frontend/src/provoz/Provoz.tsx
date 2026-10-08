import { useState } from "react";

import { Blok, BlokTelo, Obrazovka, useZpet } from "../komponenty/Obrazovka";
import { Pole } from "../komponenty/Pole";
import { Tlacitko } from "../komponenty/Tlacitko";
import { Zaskrtavatka, Zaskrtavatko } from "../komponenty/Zaskrtavatko";
import { useNabidky } from "../lety/api";
import { VolbaLetiste } from "../lety/VyberMista";
import { proHledani } from "../text";
import { useMujProvoz, useZmenitProvoz } from "./api";
import "../komponenty/Volby.css";
import "./Provoz.css";

// Můj provoz (docs/modul-muj-provoz.md, maketa muj-provoz-mobil.html): letiště a osoby
// v provozu na dnešek, jen pro tuto relaci. Otevírá se z nabídky uživatele (a štítku letiště
// v hlavičce); Zpět vrací tam, odkud uživatel přišel.

/** Letiště pro dnešek: domovské, nebo jiné (rychlá volba, ostatní přes Hledat…); ťuknutí
 *  uloží a vrátí zpět. */
export function LetisteProDnesek() {
  const zpet = useZpet();
  const nabidky = useNabidky().data;
  const provoz = useMujProvoz().data;
  const zmenit = useZmenitProvoz();
  if (!nabidky || !provoz) {
    return <Obrazovka zpet={zpet} zpetPopis="Zpět" nadpis="Letiště pro dnešek">{null}</Obrazovka>;
  }
  const mojeId = provoz.letiste?.id;
  const vybrat = (letiste_id: number | null) =>
    zmenit.mutate({ cesta: "/letiste", data: { letiste_id } }, { onSuccess: zpet });
  const domovske = nabidky.letiste.find((l) => l.domovske);
  return (
    <Obrazovka zpet={zpet} zpetPopis="Zpět" nadpis="Letiště pro dnešek">
      {domovske && (
        <Blok nadpis="Domovské">
          <BlokTelo>
            <div className="cipy">
              <Tlacitko aria-pressed={domovske.id === mojeId} onClick={() => vybrat(null)}>
                {domovske.kod} {domovske.nazev}
              </Tlacitko>
            </div>
          </BlokTelo>
        </Blok>
      )}
      <Blok nadpis="Jiné letiště" vpravo="platí do konce dne">
        <BlokTelo>
          <VolbaLetiste
            letiste={nabidky.letiste.filter((l) => !l.domovske)}
            vybrane={mojeId}
            vybrat={vybrat}
          />
        </BlokTelo>
      </Blok>
      <p className="male seda">
        Výchozí místo vzletu a přistání nových letů, sluneční časy a konec dne. Jen pro vás na
        tomto zařízení; zítra zase {domovske?.kod ?? "domovské letiště"}.
      </p>
    </Obrazovka>
  );
}

/** „1 vybraná“, „3 vybrané“, „8 vybraných“ */
function vybranych(n: number) {
  return `${n} ${n === 1 ? "vybraná" : n >= 2 && n <= 4 ? "vybrané" : "vybraných"}`;
}

/** Osoby v provozu: aktivní osoby se zaškrtávátkem (uloží se hned); rychlá volba posádky pak
 *  nabízí jen je. Zrušit výběr = nabízet všechny. */
export function OsobyVProvozu() {
  const zpet = useZpet();
  const nabidky = useNabidky().data;
  const provoz = useMujProvoz().data;
  const zmenit = useZmenitProvoz();
  const [hledat, setHledat] = useState("");
  const [jenVybrane, setJenVybrane] = useState(false);
  if (!nabidky || !provoz) {
    return <Obrazovka zpet={zpet} zpetPopis="Zpět" nadpis="Osoby v provozu">{null}</Obrazovka>;
  }
  const pocet = provoz.osoby.length;
  const h = proHledani(hledat.trim());
  const osoby = nabidky.osoby.filter(
    (o) =>
      (!jenVybrane || provoz.osoby.includes(o.id)) &&
      (!h || proHledani(`${o.prijmeni} ${o.jmeno}`).includes(h)),
  );
  return (
    <Obrazovka
      zpet={zpet}
      zpetPopis="Zpět"
      nadpis="Osoby v provozu"
      vpravo={<span className="male seda">{vybranych(pocet)}</span>}
      akce={
        <Tlacitko
          varianta="obrys"
          disabled={pocet === 0}
          onClick={() => zmenit.mutate({ cesta: "/osoby/zrusit" })}
        >
          Zrušit výběr – nabízet všechny
        </Tlacitko>
      }
    >
      <div className="provoz-hledani">
        <Pole popisek="Hledat jméno" value={hledat} onChange={(e) => setHledat(e.target.value)} />
        <div className="segmenty">
          <Tlacitko aria-pressed={jenVybrane} onClick={() => setJenVybrane(true)}>
            Vybrané <span className="cisla">{pocet}</span>
          </Tlacitko>
          <Tlacitko aria-pressed={!jenVybrane} onClick={() => setJenVybrane(false)}>
            Všechny
          </Tlacitko>
        </div>
      </div>
      <div className="osoby-v-provozu">
        <Zaskrtavatka>
          {osoby.map((o) => (
            <Zaskrtavatko
              key={o.id}
              popisek={`${o.prijmeni} ${o.jmeno}`}
              zaskrtnuto={provoz.osoby.includes(o.id)}
              zmenit={(ma) => zmenit.mutate({ cesta: "/osoby", data: { osoba_id: o.id, ma } })}
            />
          ))}
        </Zaskrtavatka>
      </div>
    </Obrazovka>
  );
}
