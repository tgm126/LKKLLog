import { useState, type ReactNode } from "react";
import { useNavigate } from "react-router";

import { Hlaska } from "../komponenty/Hlaska";
import { Obrazovka } from "../komponenty/Obrazovka";
import { Tlacitko } from "../komponenty/Tlacitko";
import { useNabidky, type Nabidky } from "./api";
import {
  BlokDalsichUdaju,
  BlokPob,
  BlokPrezkouseni,
  BlokUcelu,
  BlokUlohy,
  BlokVleku,
  BlokyPosadky,
  BlokZpusobu,
  DlazdiceLetadel,
  Dokonceni,
  ProbehlyLet,
  useNovyLet,
} from "./novyLet";
import { PolovinaPasku } from "./Pasek";
import "../komponenty/Volby.css";
import "./Pruvodce.css";

// Průvodce novým letem (mobil) podle makety docs/navrhy/pruvodce-mobil-v4.html:
// 1 letadlo → 2 posádka (u přezkoušení i jeho typ) → 3 let (u kluzáku vzlet a vlek, úloha, další údaje) → VZLET TEĎ /
// Naplánovat / Proběhlý let (výběr časů prstem). Od kroku 2 je nahoře rozpracovaný pásek
// letu, který se plní s každou volbou. Stav a bloky sdílí desktop (novyLet.tsx).

type Krok = 1 | 2 | 3 | "casy";

export function Pruvodce() {
  const { data: nabidky, error } = useNabidky();
  const navigate = useNavigate();
  const zavrit = () => navigate("/", { replace: true });
  if (!nabidky) {
    return (
      <Obrazovka zpet={zavrit} zpetPopis="Zavřít" nadpis="Nový let">
        {error && <Hlaska>{error.message}</Hlaska>}
      </Obrazovka>
    );
  }
  return <PruvodceKroky nabidky={nabidky} zavrit={zavrit} />;
}

/** Ukazatel postupu pod horní lištou: tři díly, hotové modře. */
function Postup({ krok }: { krok: Krok }) {
  const hotovo = krok === "casy" ? 3 : krok;
  return (
    <div className="postup" aria-hidden>
      {[1, 2, 3].map((k) => (
        <span key={k} className={k <= hotovo ? "hotovo" : undefined} />
      ))}
    </div>
  );
}

const NADPIS_KROKU: Record<Krok, string> = {
  1: "1 / 3 · Letadlo",
  2: "2 / 3 · Posádka",
  3: "3 / 3 · Let",
  casy: "Proběhlý let",
};

function PruvodceKroky({ nabidky, zavrit }: { nabidky: Nabidky; zavrit: () => void }) {
  const n = useNovyLet(nabidky, zavrit);
  const [krok, setKrok] = useState<Krok>(1);
  const { letadlo, rozpracovany } = n;

  const zpet = () => {
    n.setUpravuji(null);
    if (krok === 1) zavrit();
    else setKrok(krok === "casy" ? 3 : ((krok - 1) as Krok));
  };
  const spolecne = {
    zpet,
    zpetPopis: krok === 1 ? ("Zavřít" as const) : ("Zpět" as const),
    nadpis: krok === 1 || !letadlo ? "Nový let" : letadlo.rejstrik,
    vpravo: <span className="nadpisek">{NADPIS_KROKU[krok]}</span>,
    pod: <Postup krok={krok} />,
  };

  // --- krok 1: letadlo -----------------------------------------------------------------------
  if (krok === 1 || !letadlo || !rozpracovany) {
    return (
      <Obrazovka {...spolecne}>
        <DlazdiceLetadel n={n} poVyberu={() => setKrok(2)} />
      </Obrazovka>
    );
  }

  const pasek = (cas?: ReactNode) => (
    <div className="let panel-letu rozpracovany">
      <PolovinaPasku
        let={rozpracovany}
        cas={
          cas ??
          (n.aerovlek && n.novy.vlecna ? (
            <>
              <b>{n.novy.vlecna.rejstrik}</b>
              <span className="male seda">vlečná</span>
            </>
          ) : (
            <span className="male seda">nový</span>
          ))
        }
      />
    </div>
  );

  // --- krok 2: posádka -----------------------------------------------------------------------
  if (krok === 2) {
    return (
      <Obrazovka
        {...spolecne}
        akce={
          <Tlacitko
            varianta="modre"
            hlavni
            disabled={!n.posadkaHotova || n.chybiPrezkouseni}
            onClick={() => {
              n.setUpravuji(null);
              setKrok(3);
            }}
          >
            Dál
          </Tlacitko>
        }
      >
        {pasek()}
        <BlokUcelu n={n} />
        <BlokPrezkouseni n={n} />
        <BlokyPosadky n={n} />
        <BlokPob n={n} />
      </Obrazovka>
    );
  }

  // --- proběhlý let --------------------------------------------------------------------------
  if (krok === "casy") {
    return (
      <ProbehlyLet
        n={n}
        obal={({ cas, bloky, akce }) => (
          <Obrazovka {...spolecne} akce={akce}>
            {pasek(cas)}
            {bloky}
          </Obrazovka>
        )}
      />
    );
  }

  // --- krok 3: let ---------------------------------------------------------------------------
  return (
    <Obrazovka {...spolecne} akce={<Dokonceni n={n} probehly={() => setKrok("casy")} />}>
      {pasek()}
      <BlokZpusobu n={n} />
      <BlokVleku n={n} />
      <BlokUlohy n={n} />
      <BlokDalsichUdaju n={n} />
    </Obrazovka>
  );
}
