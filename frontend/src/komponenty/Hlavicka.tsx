import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { NavLink } from "react-router";

import { poslat, type Ja } from "../api";
import { denSlovy, hodinyMinuty, hodinyMinutySekundy } from "../cas";
import { useDen } from "../lety/api";
import { useTik } from "../tik";
import { nacistRezim, nastavitRezim, REZIMY, type Rezim } from "../rezim";
import { inicialy, zmenitUzivatele } from "../uzivatel";
import { Tlacitko } from "./Tlacitko";
import "./Hlavicka.css";

export function Hlavicka({ ja }: { ja: Ja }) {
  return (
    <>
      <header className="hlavicka">
        <div className="hlavicka-radek">
          <span className="velke tucne">AK Kladno Log</span>
          <span className="hlavicka-vpravo">
            <CasUtc />
            <NabidkaUzivatele ja={ja} />
          </span>
        </div>
        <DenASlunce />
      </header>
      <nav className="menu">
        <NavLink className="nadpisek" to="/" end>
          Lety
        </NavLink>
      </nav>
    </>
  );
}

function CasUtc() {
  const ted = useTik();
  return (
    <span>
      <span className="velke tucne cisla">{hodinyMinutySekundy(ted)}</span>{" "}
      <span className="male seda">UTC</span>
    </span>
  );
}

/** Den a sluneční časy domovského letiště (TB začátek a TE konec občanského soumraku). */
function DenASlunce() {
  const den = useDen().data;
  if (!den) return null;
  const { tb, sr, ss, te } = den.slunce;
  const casy: [string, string | null][] = [["TB", tb], ["SR", sr], ["SS", ss], ["TE", te]];
  return (
    <div className="hlavicka-radek cisla">
      <span>{denSlovy(den.den)}</span>
      {tb && (
        <span>
          {casy.map(([zkratka, cas], i) => (
            <span key={zkratka}>
              {i > 0 && " · "}
              <b>{zkratka}</b> {cas && hodinyMinuty(cas)}
            </span>
          ))}
        </span>
      )}
    </div>
  );
}

function NabidkaUzivatele({ ja }: { ja: Ja }) {
  const [otevrena, setOtevrena] = useState(false);
  const [rezim, setRezim] = useState<Rezim>(nacistRezim);
  const qc = useQueryClient();
  const odhlasit = useMutation({
    mutationFn: () => poslat("/odhlaseni"),
    onSettled: () => zmenitUzivatele(qc, null),
  });

  // Zavřít klávesou Esc; ťuknutí mimo nabídku zachytí zástin (neprojde na pásek pod ním).
  useEffect(() => {
    if (!otevrena) return;
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setOtevrena(false);
    document.addEventListener("keydown", esc);
    return () => document.removeEventListener("keydown", esc);
  }, [otevrena]);

  return (
    <span>
      <button
        className="kulate"
        aria-label="Nabídka uživatele"
        aria-expanded={otevrena}
        onClick={() => setOtevrena(!otevrena)}
      >
        {inicialy(ja)}
      </button>
      {otevrena && <div className="zastin" onClick={() => setOtevrena(false)} />}
      {otevrena && (
        <div className="nabidka">
          <div className="nabidka-kdo">
            <div className="tucne">
              {ja.jmeno} {ja.prijmeni}
            </div>
            <div className="male seda">{ja.email}</div>
          </div>
          <span className="nadpisek">Režim zobrazení</span>
          {REZIMY.map((r) => (
            <Tlacitko
              key={r.rezim}
              varianta="bez-ramu"
              aria-pressed={rezim === r.rezim}
              onClick={() => {
                nastavitRezim(r.rezim);
                setRezim(r.rezim);
                setOtevrena(false);
              }}
            >
              {r.nazev}
            </Tlacitko>
          ))}
          <Tlacitko varianta="obrys" disabled={odhlasit.isPending} onClick={() => odhlasit.mutate()}>
            Odhlásit
          </Tlacitko>
        </div>
      )}
    </span>
  );
}
