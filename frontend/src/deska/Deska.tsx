import { useEffect, useState } from "react";
import { Outlet, useMatch, useNavigate } from "react-router";

import { denSlovy, hodinyMinutySekundy } from "../cas";
import { Hlaska } from "../komponenty/Hlaska";
import { Oznameni, useZprava } from "../komponenty/Oznameni";
import { Tlacitko } from "../komponenty/Tlacitko";
import { useAkceLetu } from "../lety/akce";
import { useDen, useLety, useNabidky, useSouhrnDne } from "../lety/api";
import { useSirokaDeska } from "../rozvrzeni";
import { useJa } from "../uzivatel";
import { CasovaOsa } from "./CasovaOsa";
import { DenikDne } from "./DenikDne";
import { Lista } from "./Lista";
import { Pasky } from "./Pasky";
import { RadaLetadel } from "./RadaLetadel";
import { Souhrny } from "./Souhrny";
import "./Deska.css";

// Provozní deska – desktop (docs/modul-desktop.md, maketa docs/navrhy/provoz-desktop-v7.html):
// jedna obrazovka na celý provoz dne pro myš. Lišta, řada letadel, vlevo pásky (ve vzduchu,
// naplánované), uprostřed deník dne, vpravo souhrny, dole časová osa. Detail letu a nový let
// vyjedou jako panel zprava (vnořené adresy /let/:id a /novy-let) – deska zůstává ovladatelná.
// Klávesy: N nový let, Esc zavře panel, Ctrl+Z vrátí poslední akci (dokud je vidět ZPĚT).

export function Deska() {
  const ja = useJa().data!;
  /** Zobrazený den; prázdný = dnešek (jinak jen deník, souhrny a osa toho dne). */
  const [den, setDen] = useState<string>();
  const dnesni = useDen().data;
  const zobrazeny = useDen(den).data;
  const dnesniLety = useLety();
  const letyDne = useLety(den);
  const souhrnDne = useSouhrnDne(den);
  const nabidky = useNabidky().data;
  const siroka = useSirokaDeska();
  const [souhrny, setSouhrny] = useState(false);
  const navigate = useNavigate();
  const detail = useMatch("/let/:id");
  const novy = useMatch("/novy-let");
  const panel = !!detail || !!novy;
  const vybranyId = detail ? Number(detail.params.id) : null;
  const akce = useAkceLetu();
  const { zprava, oznamit } = useZprava();

  useEffect(() => {
    const klavesa = (e: KeyboardEvent) => {
      const vPoli = (e.target as HTMLElement).closest("input, textarea, select");
      if (vPoli || e.altKey || e.metaKey) return;
      if (e.key === "Escape" && panel) navigate("/");
      else if (e.key.toLowerCase() === "n" && !e.ctrlKey && !ja.jen_cteni) {
        e.preventDefault();
        navigate("/novy-let");
      } else if (e.key.toLowerCase() === "z" && e.ctrlKey && zprava?.zpet) {
        e.preventDefault();
        zprava.zpet();
        oznamit(null);
      }
    };
    document.addEventListener("keydown", klavesa);
    return () => document.removeEventListener("keydown", klavesa);
  }, [panel, navigate, zprava, oznamit, ja.jen_cteni]);

  const jinyDen = den !== undefined;
  const lety = letyDne.data ?? [];
  const poradi = nabidky?.letadla.map((a) => a.rejstrik) ?? [];
  const mojeKod = dnesni?.letiste?.kod;
  // Zpět na dnešek je den prázdný (stejný dotaz jako pásky)
  const zmenitDen = (novyDen: string) => setDen(dnesni && novyDen < dnesni.den ? novyDen : undefined);

  return (
    <div className="deska">
      {dnesni && zobrazeny && (
        <Lista
          ja={ja}
          den={zobrazeny}
          dnes={dnesni.den}
          zmenitDen={zmenitDen}
          siroka={siroka}
          souhrny={souhrny}
          prepnoutSouhrny={() => setSouhrny(!souhrny)}
        />
      )}
      {jinyDen && (
        <div className="pruh-jineho-dne">
          Prohlížíte {denSlovy(den).toLocaleLowerCase("cs-CZ")} – deník dne (pásky jsou jen u dneška)
          <Tlacitko varianta="modre" onClick={() => setDen(undefined)}>
            Zpět na dnešek
          </Tlacitko>
        </div>
      )}
      {nabidky && <RadaLetadel
          letadla={nabidky.letadla}
          lety={dnesniLety.data ?? []}
          mojeKod={mojeKod}
          domovskeKod={nabidky.letiste.find((l) => l.domovske)?.kod}
          nazvyKategorii={siroka}
        />}
      <div className="deska-spodek">
        {letyDne.error && (
          <Hlaska>
            Bez spojení se serverem – údaje z {hodinyMinutySekundy(new Date(letyDne.dataUpdatedAt))} UTC.
          </Hlaska>
        )}
        <div className={["deska-sloupce", siroka && "siroka", jinyDen && "jiny-den"].filter(Boolean).join(" ")}>
          {!jinyDen && (
            <section className="deska-sloupec" aria-label="Pásky">
              <Pasky lety={dnesniLety.data ?? []} mojeKod={mojeKod} vybranyId={vybranyId} akce={akce} />
            </section>
          )}
          <section className="deska-sloupec deska-denik" aria-label="Deník dne">
            <DenikDne lety={lety} vybranyId={vybranyId} />
          </section>
          {(siroka || souhrny) && (
            <aside className={siroka ? "deska-sloupec" : "deska-sloupec souhrny-vysunute"} aria-label="Souhrny dne">
              <Souhrny souhrn={souhrnDne.data ?? []} poradi={poradi} />
            </aside>
          )}
        </div>
        {zobrazeny && (
          <CasovaOsa lety={lety} den={zobrazeny} poradi={poradi} vybranyId={vybranyId} dnes={!jinyDen} />
        )}
        <Outlet />
      </div>
      <div className="deska-oznameni">
        <Oznameni />
      </div>
      {akce.dialog}
    </div>
  );
}
