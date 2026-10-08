import { useNavigate } from "react-router";

import { doba, hodinyMinuty } from "../cas";
import type { Pasek } from "../lety/api";
import { podle } from "../lety/poradi";

// Deník dne (docs/modul-desktop.md 3.3): jeden řádek na let – letadlo · posádka (PIC · druhá
// osoba s funkcí) · vzlet · přistání · P · doba; ostatní údaje jsou v detailu. Ukončené
// od posledního přistání, pod nimi zrušené; patička s celkem (lety · přistání · doba).

function Radek({ let: l, vybrany }: { let: Pasek; vybrany: boolean }) {
  const navigate = useNavigate();
  const zrusen = l.stav === "ZRUSEN";
  const [pic, druha] = l.posadka;
  return (
    <button
      type="button"
      className={["radek-deniku", zrusen && "zrusen", vybrany && "vybrany"].filter(Boolean).join(" ")}
      title={l.posadka.map((c) => `${c.jmeno} ${c.prijmeni} (${c.funkce})`).join(", ")}
      onClick={() => navigate(`/let/${l.id}`)}
    >
      <span className="tucne">{l.rejstrik}</span>
      <span>
        {pic && `${pic.jmeno} ${pic.prijmeni}`}
        {druha && (
          <>
            {" · "}
            {druha.jmeno} {druha.prijmeni} <span className="male seda">{druha.funkce.toLocaleLowerCase("cs-CZ")}</span>
          </>
        )}
      </span>
      <span className="cisla">{l.cas_vzletu && hodinyMinuty(l.cas_vzletu)}</span>
      <span className="cisla">{l.cas_pristani && hodinyMinuty(l.cas_pristani)}</span>
      <span className="cisla vpravo">{!zrusen && l.pocet_pristani}</span>
      <span className="cisla vpravo tucne">{!zrusen && doba(l.doba_uctovana_min ?? 0)}</span>
    </button>
  );
}

export function DenikDne({ lety, vybranyId }: { lety: Pasek[]; vybranyId: number | null }) {
  const ukoncene = lety.filter((l) => l.stav === "UKONCEN").sort(podle((l) => l.cas_pristani, true));
  const zrusene = lety.filter((l) => l.stav === "ZRUSEN").sort(podle((l) => l.zruseno, true));
  const minut = ukoncene.reduce((s, l) => s + (l.doba_uctovana_min ?? 0), 0);
  const pristani = ukoncene.reduce((s, l) => s + (l.pocet_pristani ?? 0), 0);
  return (
    <>
      <h2 className="nadpis-sloupce">
        <span className="nadpisek">Deník dne</span>
        <span className="male seda">
          ukončené {ukoncene.length} · zrušené {zrusene.length}
        </span>
      </h2>
      <div className="denik-deska">
        <div className="radek-deniku zahlavi" aria-hidden>
          <span>Letadlo</span>
          <span>Posádka</span>
          <span>↑</span>
          <span>↓</span>
          <span className="vpravo">P</span>
          <span className="vpravo">Doba</span>
        </div>
        <div className="denik-radky">
          {ukoncene.length === 0 && <p className="prazdny-sloupec male seda">Zatím žádný ukončený let.</p>}
          {ukoncene.map((l) => (
            <Radek key={l.id} let={l} vybrany={l.id === vybranyId} />
          ))}
          {zrusene.length > 0 && <p className="mezititulek nadpisek">Zrušené {zrusene.length}</p>}
          {zrusene.map((l) => (
            <Radek key={l.id} let={l} vybrany={l.id === vybranyId} />
          ))}
        </div>
        <p className="denik-pata male seda">
          <span>
            Lety <b className="cisla">{ukoncene.length}</b>
          </span>
          <span>
            Přistání <b className="cisla">{pristani}</b>
          </span>
          <span>
            Doba <b className="cisla">{doba(minut)}</b>
          </span>
          <span className="vpravo-auto">doba = účtovaná, nejméně 1 minuta</span>
        </p>
      </div>
    </>
  );
}
