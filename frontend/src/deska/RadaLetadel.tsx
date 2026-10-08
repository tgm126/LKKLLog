import { useNavigate } from "react-router";

import { doba, stopky } from "../cas";
import { Tlacitko } from "../komponenty/Tlacitko";
import type { LetadloNabidka, Pasek } from "../lety/api";
import "../lety/PanelLetu.css";
import { useTik } from "../tik";
import { useJenCteni } from "../uzivatel";

// Řada letadel pod lištou (docs/modul-desktop.md 3.1): všechna letadla podle kategorie,
// neutrální rámeček se stavem jen proužkem vlevo (zelený letí, modrý naplánované) a dnešek:
// běžící čas, nebo počet letů a nálet, a oranžově kde letadlo je – poslední evidované
// přistání (v_lov_letadlo.poloha), jen když není na domovském ani na mém letišti
// (rozhodnuto 8. 10. 2026). Klik na letadlo na zemi = nový let s ním (místo vzletu = poloha);
// na letící nebo naplánované = detail.

export function RadaLetadel({
  letadla,
  lety,
  mojeKod,
  domovskeKod,
  nazvyKategorii,
}: {
  letadla: LetadloNabidka[];
  /** Moje letiště (můj provoz) a domovské – poloha se ukáže, jen když je jinde než obě. */
  mojeKod: string | undefined;
  domovskeKod: string | undefined;
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
        <Tlacitko
          varianta="modre"
          hlavni
          className="novy-let"
          title="Nový let (klávesa N)"
          onClick={() => navigate("/novy-let")}
        >
          Nový let
        </Tlacitko>
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
              const jinde = !leti && a.poloha !== null && a.poloha !== mojeKod && a.poloha !== domovskeKod && a.poloha;
              const otevreny = leti ?? plan;
              const stav = a.mimo_provoz ? "mimo" : leti ? "vzduch" : plan ? "naplanovan" : "";
              const popis = a.mimo_provoz
                ? "mimo provoz"
                : leti?.cas_vzletu
                  ? `letí ${stopky(leti.cas_vzletu, ted).slice(0, -3)}`
                  : plan
                    ? "naplánován"
                    : dnes.length > 0
                      ? doba(dnes.reduce((s, l) => s + (l.doba_uctovana_min ?? 0), 0))
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
                    {jinde && <span className="jinde"> · {jinde}</span>}
                  </span>
                </button>
              );
            })}
        </div>
      ))}
    </nav>
  );
}
