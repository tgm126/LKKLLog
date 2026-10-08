import { useNavigate } from "react-router";

import { doba, stopky } from "../cas";
import type { LetadloNabidka, Pasek } from "../lety/api";
import { useTik } from "../tik";
import { useJenCteni } from "../uzivatel";

// Řada letadel pod lištou (docs/modul-desktop.md 3.1): všechna letadla podle kategorie,
// neutrální rámeček se stavem jen proužkem vlevo (zelený letí, modrý naplánované) a dnešek:
// běžící čas, nebo počet letů a nálet, oranžově kde letadlo je (přistálo jinde než na mém
// letišti). Klik na letadlo na zemi = nový let s ním; na letící nebo naplánované = detail.

/** Kde letadlo je: místo posledního dnešního přistání, když není moje letiště (jinak null). */
function kdeJe(lety: Pasek[], rejstrik: string): string | null {
  const posledni = lety
    .filter((l) => l.rejstrik === rejstrik && l.stav === "UKONCEN" && l.cas_pristani)
    .sort((a, b) => b.cas_pristani!.localeCompare(a.cas_pristani!))[0];
  return posledni?.misto_pristani ?? null;
}

export function RadaLetadel({
  letadla,
  lety,
  nazvyKategorii,
}: {
  letadla: LetadloNabidka[];
  /** Dnešní lety (stav letadel je vždy podle dneška). */
  lety: Pasek[];
  /** Názvy kategorií (na notebooku jen přepážky). */
  nazvyKategorii: boolean;
}) {
  const navigate = useNavigate();
  const ted = useTik();
  const jenCteni = useJenCteni();
  const kategorie = [...new Map(letadla.map((a) => [a.kategorie_kod, a.kategorie]))];
  return (
    <nav className="rada-letadel" aria-label="Letadla">
      {!jenCteni && (
        <button type="button" className="novy-let" onClick={() => navigate("/novy-let")}>
          + Nový let <kbd>N</kbd>
        </button>
      )}
      {kategorie.map(([kod, nazev]) => (
        <div key={kod} className="skupina-lodi">
          {nazvyKategorii && <span className="nadpisek">{nazev}</span>}
          {letadla
            .filter((a) => a.kategorie_kod === kod)
            .map((a) => {
              const leti = lety.find((l) => l.rejstrik === a.rejstrik && l.stav === "VE_VZDUCHU");
              const plan = lety.find((l) => l.rejstrik === a.rejstrik && l.stav === "NAPLANOVAN");
              const dnes = lety.filter((l) => l.rejstrik === a.rejstrik && l.stav === "UKONCEN");
              const jinde = !leti && kdeJe(lety, a.rejstrik);
              const otevreny = leti ?? plan;
              const stav = a.mimo_provoz ? "mimo" : leti ? "vzduch" : plan ? "naplanovan" : "";
              const popis = a.mimo_provoz
                ? "mimo provoz"
                : leti?.cas_vzletu
                  ? `letí ${stopky(leti.cas_vzletu, ted).slice(0, -3)}`
                  : plan
                    ? "naplánován"
                    : dnes.length > 0
                      ? `${dnes.length}× ${doba(dnes.reduce((s, l) => s + (l.doba_uctovana_min ?? 0), 0))}`
                      : "dnes nelétal";
              return (
                <button
                  key={a.id}
                  type="button"
                  className={["lod", stav].filter(Boolean).join(" ")}
                  disabled={a.mimo_provoz}
                  title={[a.typ, a.vlecne && "vlečná", a.soukrome && "soukromé"].filter(Boolean).join(" · ")}
                  onClick={() => {
                    if (otevreny) navigate(`/let/${otevreny.id}`);
                    // jen ke čtení: letadlo na zemi nic nezaloží
                    else if (!jenCteni) navigate("/novy-let", { state: { letadloId: a.id } });
                  }}
                >
                  <b className="rejstrik-lodi">{a.rejstrik}</b>
                  <span className="male seda cisla">
                    {popis}
                    {jinde && <span className="jinde"> · na {jinde}</span>}
                  </span>
                </button>
              );
            })}
        </div>
      ))}
    </nav>
  );
}
