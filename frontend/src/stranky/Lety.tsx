import { useNavigate } from "react-router";

import { doba, hodinyMinutySekundy } from "../cas";
import { Hlaska } from "../komponenty/Hlaska";
import { Oznameni } from "../komponenty/Oznameni";
import { Sekce } from "../komponenty/Sekce";
import { Tlacitko } from "../komponenty/Tlacitko";
import { useAkceLetu } from "../lety/akce";
import { useLety, type Pasek, type Stav } from "../lety/api";
import { PasekNaplanovany, PasekUkonceny, PasekVeVzduchu, PasekZruseny } from "../lety/Pasek";

const podle =
  (klic: (l: Pasek) => string | null, sestupne = false) =>
  (a: Pasek, b: Pasek) =>
    (klic(a) ?? "").localeCompare(klic(b) ?? "") * (sestupne ? -1 : 1);

/** Vlek (kluzák + jeho vlečná ve stejném stavu) jako jedna dvojice – naplánovaný i ve vzduchu. */
function dvojice(lety: Pasek[]): Pasek[][] {
  const podleId = new Map(lety.map((l) => [l.id, l]));
  const vlecne = new Set(
    lety.flatMap((l) => (l.vlecny_let_id && podleId.has(l.vlecny_let_id) ? [l.vlecny_let_id] : [])),
  );
  return lety
    .filter((l) => !vlecne.has(l.id))
    .map((l) => {
      const vlecna = l.vlecny_let_id ? podleId.get(l.vlecny_let_id) : undefined;
      return vlecna ? [l, vlecna] : [l];
    });
}

/** Přehled letů dne: ve vzduchu, naplánované, ukončené, zrušené (maketa lety-mobil.html). */
export function Lety() {
  const { data: lety, error, dataUpdatedAt } = useLety();
  const { provest, probiha } = useAkceLetu();
  const navigate = useNavigate();
  const dole = (
    <div className="dole">
      <Oznameni />
      <Tlacitko varianta="modre" hlavni onClick={() => navigate("/novy-let")}>
        + Nový let
      </Tlacitko>
    </div>
  );
  if (!lety) {
    return (
      <>
        <main className="obsah">{error && <Hlaska>{error.message}</Hlaska>}</main>
        {dole}
      </>
    );
  }
  const akce = (lety: Pasek[]) => ({
    provest,
    zaneprazdnen: lety.some((l) => l.id === probiha?.letId),
  });
  const ve = (stav: Stav) => lety.filter((l) => l.stav === stav);
  const veVzduchu = dvojice(ve("VE_VZDUCHU").sort(podle((l) => l.cas_vzletu)));
  const naplanovane = dvojice(ve("NAPLANOVAN").sort(podle((l) => l.zalozeno)));
  const ukoncene = ve("UKONCEN").sort(podle((l) => l.cas_pristani, true));
  const zrusene = ve("ZRUSEN").sort(podle((l) => l.zruseno, true));
  const celkem = ukoncene.reduce((s, l) => s + (l.doba_uctovana_min ?? 0), 0);

  return (
    <>
    <main className="obsah">
      {error && (
        <Hlaska>
          Bez spojení se serverem – údaje z {hodinyMinutySekundy(new Date(dataUpdatedAt))} UTC.
        </Hlaska>
      )}
      {lety.length === 0 && <p className="seda">Dnes zatím žádné lety.</p>}
      {veVzduchu.length > 0 && (
        <Sekce nadpis={`Ve vzduchu ${veVzduchu.length}`}>
          {veVzduchu.map((d) => (
            <PasekVeVzduchu key={d[0]!.id} lety={d} {...akce(d)} />
          ))}
        </Sekce>
      )}
      {naplanovane.length > 0 && (
        <Sekce nadpis={`Naplánované ${naplanovane.length}`}>
          {naplanovane.map((d) => (
            <PasekNaplanovany key={d[0]!.id} lety={d} {...akce(d)} />
          ))}
        </Sekce>
      )}
      {ukoncene.length > 0 && (
        <Sekce nadpis={`Ukončené ${ukoncene.length}`} vpravo={`celkem ${doba(celkem)}`}>
          {ukoncene.map((l) => (
            <PasekUkonceny key={l.id} let={l} />
          ))}
        </Sekce>
      )}
      {zrusene.length > 0 && (
        <Sekce nadpis={`Zrušené ${zrusene.length}`} sbalena>
          {zrusene.map((l) => (
            <PasekZruseny key={l.id} let={l} />
          ))}
        </Sekce>
      )}
    </main>
    {dole}
    </>
  );
}
