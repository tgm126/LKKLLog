import { doba, hodinyMinutySekundy } from "../cas";
import { Hlaska } from "../komponenty/Hlaska";
import { Sekce } from "../komponenty/Sekce";
import { useLety, type Pasek, type Stav } from "../lety/api";
import { PasekNaplanovany, PasekUkonceny, PasekVeVzduchu, PasekZruseny } from "../lety/Pasek";

const podle =
  (klic: (l: Pasek) => string | null, sestupne = false) =>
  (a: Pasek, b: Pasek) =>
    (klic(a) ?? "").localeCompare(klic(b) ?? "") * (sestupne ? -1 : 1);

/** Naplánované: vlek (kluzák + jeho naplánovaná vlečná) jako jedna dvojice. */
function dvojice(naplanovane: Pasek[]): Pasek[][] {
  const podleId = new Map(naplanovane.map((l) => [l.id, l]));
  const vlecne = new Set(naplanovane.flatMap((l) => (l.vlecny_let_id ? [l.vlecny_let_id] : [])));
  return naplanovane
    .filter((l) => !vlecne.has(l.id))
    .map((l) => {
      const vlecna = l.vlecny_let_id ? podleId.get(l.vlecny_let_id) : undefined;
      return vlecna ? [l, vlecna] : [l];
    });
}

/** Přehled letů dne: ve vzduchu, naplánované, ukončené, zrušené (maketa lety-mobil.html). */
export function Lety() {
  const { data: lety, error, dataUpdatedAt } = useLety();
  if (!lety) {
    return <main className="obsah">{error && <Hlaska>{error.message}</Hlaska>}</main>;
  }
  const ve = (stav: Stav) => lety.filter((l) => l.stav === stav);
  const veVzduchu = ve("VE_VZDUCHU").sort(podle((l) => l.cas_vzletu));
  const naplanovane = dvojice(ve("NAPLANOVAN").sort(podle((l) => l.zalozeno)));
  const ukoncene = ve("UKONCEN").sort(podle((l) => l.cas_pristani, true));
  const zrusene = ve("ZRUSEN").sort(podle((l) => l.zruseno, true));
  const celkem = ukoncene.reduce((s, l) => s + (l.doba_uctovana_min ?? 0), 0);

  return (
    <main className="obsah">
      {error && (
        <Hlaska>
          Bez spojení se serverem – údaje z {hodinyMinutySekundy(new Date(dataUpdatedAt))} UTC.
        </Hlaska>
      )}
      {lety.length === 0 && <p className="seda">Dnes zatím žádné lety.</p>}
      {veVzduchu.length > 0 && (
        <Sekce nadpis={`Ve vzduchu ${veVzduchu.length}`}>
          {veVzduchu.map((l) => (
            <PasekVeVzduchu key={l.id} let={l} />
          ))}
        </Sekce>
      )}
      {naplanovane.length > 0 && (
        <Sekce nadpis={`Naplánované ${naplanovane.length}`}>
          {naplanovane.map((d) => (
            <PasekNaplanovany key={d[0]!.id} lety={d} />
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
  );
}
