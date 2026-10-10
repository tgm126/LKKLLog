import { useState, type ReactNode } from "react";
import { useLocation, useNavigate } from "react-router";

import { Hlaska } from "../komponenty/Hlaska";
import { Blok, BlokTelo } from "../komponenty/Obrazovka";
import { Panel } from "../komponenty/Panel";
import { Tlacitko } from "../komponenty/Tlacitko";
import { Udaj, Udaje } from "../komponenty/Udaje";
import { useNabidky, type Nabidky } from "../lety/api";
import {
  BlokDalsichUdaju,
  BlokPob,
  BlokUcelu,
  BlokPrezkouseni,
  BlokUlohy,
  BlokVleku,
  BlokyPosadky,
  BlokZpusobu,
  chybi,
  DlazdiceLetadel,
  Dokonceni,
  ProbehlyLet,
  useNovyLet,
  type NovyLet,
} from "../lety/novyLet";
import type { LetPasku } from "../lety/Pasek";
import { useMujProvoz } from "../provoz/api";
import { PasekDeska } from "./PasekDeska";
import "../lety/Pruvodce.css";

// Nový let v panelu zprava (docs/modul-desktop.md 3.8): jeden formulář místo průvodce –
// nahoře rozpracovaný pásek (u aerovleku dvojice), vlevo letadlo, účel, způsob vzletu a vlek,
// vpravo posádka, úloha a další údaje; v patičce VZLET TEĎ · Naplánovat · Proběhlý let.
// Vybrané letadlo se sbalí do jednoho řádku (mřížka dlaždic by vytlačila účel a vlek pod
// okraj okna na notebooku); klik na řádek mřížku zase rozbalí.
// Stav, pravidla a bloky jsou stejné jako v mobilním průvodci (lety/novyLet.tsx).

export function PanelNovehoLetu() {
  const { data: nabidky, error } = useNabidky();
  const navigate = useNavigate();
  // Klik na letadlo v řadě letadel: formulář s tímto letadlem (jiné letadlo = nový formulář)
  const letadloId = (useLocation().state as { letadloId?: number } | null)?.letadloId;
  const zavrit = () => navigate("/");
  if (!nabidky) {
    return (
      <Panel nadpis="Nový let" siroky zavrit={zavrit} hlava={<h2 className="velke tucne">Nový let</h2>}>
        {error && <Hlaska>{error.message}</Hlaska>}
      </Panel>
    );
  }
  return <Formular key={letadloId ?? "bez"} nabidky={nabidky} letadloId={letadloId} zavrit={zavrit} />;
}

/** Co ještě chybí k uložení (do patičky). */
function coChybi(n: NovyLet): string[] {
  if (!n.letadlo) return ["letadlo"];
  return [
    ...n.pole.filter((p) => !n.novy.osoby[p.funkceId]).map((p) => (p.kod === "PIC" ? "pilot" : p.nazev)),
    n.ulohaPovinna && n.novy.uloha === undefined ? "úloha" : "",
    n.chybiPrezkouseni ? "přezkoušení" : "",
    n.aerovlek && (!n.novy.vlecna || !n.novy.vlekar) ? "vlečná a vlekař" : "",
  ].filter(Boolean);
}

function Formular({
  nabidky,
  letadloId,
  zavrit,
}: {
  nabidky: Nabidky;
  letadloId: number | undefined;
  zavrit: () => void;
}) {
  const n = useNovyLet(nabidky, zavrit, letadloId);
  const [probehly, setProbehly] = useState(false);
  const [menimLetadlo, setMenimLetadlo] = useState(false);
  const letiste = useMujProvoz().data?.letiste;
  const mojeKod = letiste?.kod;
  const hlava = (
    <>
      <h2 className="velke tucne">Nový let</h2>
      <span className="seda">dnes{letiste && ` · ${letiste.kod} ${letiste.nazev}`}</span>
    </>
  );

  // Rozpracovaný pásek; u aerovleku dvojice s vlečnou a vlekařem
  const vlekar = nabidky.osoby.find((o) => o.id === n.novy.vlekar);
  const vlecna: LetPasku | null =
    n.aerovlek && n.novy.vlecna
      ? {
          stav: "ROZPRACOVANY",
          rejstrik: n.novy.vlecna.rejstrik,
          typ: n.novy.vlecna.typ,
          je_vlecny: true,
          ucel: null,
          ucel_kod: null,
          zpusob_vzletu: "",
          zpusob_vzletu_kod: "VLASTNI",
          cas_vzletu: null,
          vzlet_namereno: null,
          cas_pristani: null,
          doba_uctovana_min: null,
          pocet_pristani: null,
          uloha: null,
          uloha_oznaceni: null,
          prezkouseni: null,
          prezkouseni_kod: null,
          varovani: null,
          pob: 1,
          posadka: vlekar
            ? [{ jmeno: vlekar.jmeno, prijmeni: vlekar.prijmeni, funkce: "PIC", funkce_kod: "PIC" }]
            : [],
        }
      : null;
  const pasek = (cas?: ReactNode) =>
    n.rozpracovany && (
      <div className={vlecna ? "dvojice-deska rozpracovany-pasek" : "rozpracovany-pasek"}>
        <PasekDeska let={n.rozpracovany} mojeKod={mojeKod} vPanelu cas={cas} />
        {vlecna && <PasekDeska let={vlecna} mojeKod={mojeKod} vPanelu />}
      </div>
    );

  if (probehly) {
    return (
      <ProbehlyLet
        n={n}
        obal={({ cas, bloky, akce }) => (
          <Panel
            nadpis="Nový let"
            siroky
            zavrit={zavrit}
            hlava={hlava}
            pata={
              <>
                {akce}
                <Tlacitko varianta="obrys" onClick={() => setProbehly(false)}>
                  Zpět
                </Tlacitko>
              </>
            }
          >
            {pasek(cas)}
            <div className="formular-deska jednosloupcovy">{bloky}</div>
          </Panel>
        )}
      />
    );
  }

  const chybiUdaje = coChybi(n);
  return (
    <Panel
      nadpis="Nový let"
      siroky
      zavrit={zavrit}
      hlava={hlava}
      pata={
        <>
          <Dokonceni n={n} probehly={() => setProbehly(true)} />
          <span className="male seda vpravo-auto">
            {chybiUdaje.length > 0 ? `Chybí: ${chybiUdaje.join(", ").toLocaleLowerCase("cs-CZ")}` : "Vše vyplněno"}
          </span>
        </>
      }
    >
      {pasek()}
      <div className="formular-deska">
        <div>
          <Blok nadpis="Letadlo" vpravo={chybi(!n.letadlo)}>
            {n.letadlo && !menimLetadlo ? (
              <Udaje>
                <Udaj
                  popisek={n.letadlo.kategorie}
                  hodnota={
                    <>
                      <b>{n.letadlo.rejstrik}</b> <span className="seda">{n.letadlo.typ}</span>
                    </>
                  }
                  cely
                  upravit={() => setMenimLetadlo(true)}
                />
              </Udaje>
            ) : (
              <BlokTelo>
                <DlazdiceLetadel n={n} poVyberu={() => setMenimLetadlo(false)} />
              </BlokTelo>
            )}
          </Blok>
          {n.letadlo && (
            <>
              <BlokUcelu n={n} />
              <BlokPrezkouseni n={n} />
              <BlokZpusobu n={n} />
              <BlokVleku n={n} />
            </>
          )}
        </div>
        <div>
          {n.letadlo ? (
            <>
              <BlokyPosadky n={n} />
              <BlokPob n={n} />
              <BlokUlohy n={n} />
              <BlokDalsichUdaju n={n} />
            </>
          ) : (
            <p className="male seda">Nejdřív vyberte letadlo.</p>
          )}
        </div>
      </div>
    </Panel>
  );
}
