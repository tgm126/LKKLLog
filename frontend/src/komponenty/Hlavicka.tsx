import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { NavLink } from "react-router";

import { poslat, type Ja } from "../api";
import { nacistRezim, nastavitRezim, REZIMY, type Rezim } from "../rezim";
import { inicialy, zmenitUzivatele } from "../uzivatel";
import { Tlacitko } from "./Tlacitko";
import "./Hlavicka.css";

export function Hlavicka({ ja }: { ja: Ja }) {
  return (
    <>
      <header className="hlavicka">
        <div className="hlavicka-radek">
          <span className="velke tucne">LKKL Log</span>
          <span className="hlavicka-vpravo">
            <CasUtc />
            <NabidkaUzivatele ja={ja} />
          </span>
        </div>
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
  const [ted, setTed] = useState(() => new Date());
  useEffect(() => {
    const casovac = setInterval(() => setTed(new Date()), 1000);
    return () => clearInterval(casovac);
  }, []);
  return (
    <span>
      <span className="velke tucne cisla">{ted.toISOString().slice(11, 19)}</span>{" "}
      <span className="male seda">UTC</span>
    </span>
  );
}

function NabidkaUzivatele({ ja }: { ja: Ja }) {
  const [otevrena, setOtevrena] = useState(false);
  const [rezim, setRezim] = useState<Rezim>(nacistRezim);
  const obal = useRef<HTMLSpanElement>(null);
  const qc = useQueryClient();
  const odhlasit = useMutation({
    mutationFn: () => poslat("/odhlaseni"),
    onSettled: () => zmenitUzivatele(qc, null),
  });

  // Zavřít ťuknutím mimo nabídku nebo klávesou Esc.
  useEffect(() => {
    if (!otevrena) return;
    const mimo = (e: PointerEvent) => {
      if (!obal.current?.contains(e.target as Node)) setOtevrena(false);
    };
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setOtevrena(false);
    document.addEventListener("pointerdown", mimo);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("pointerdown", mimo);
      document.removeEventListener("keydown", esc);
    };
  }, [otevrena]);

  return (
    <span ref={obal}>
      <button
        className="kulate"
        aria-label="Nabídka uživatele"
        aria-expanded={otevrena}
        onClick={() => setOtevrena(!otevrena)}
      >
        {inicialy(ja)}
      </button>
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
