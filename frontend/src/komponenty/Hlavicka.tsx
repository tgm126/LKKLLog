import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { NavLink, useNavigate } from "react-router";

import { poslat, type Ja } from "../api";
import { denSlovy, hodinyMinuty, hodinyMinutySekundy } from "../cas";
import { useDen } from "../lety/api";
import { useMujProvoz } from "../provoz/api";
import { useTik } from "../tik";
import { nacistRezim, nastavitRezim, REZIMY, type Rezim } from "../rezim";
import { inicialy, zmenitUzivatele } from "../uzivatel";
import { Stitek } from "./Stitek";
import { Tlacitko } from "./Tlacitko";
import "./Volby.css";
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
        {/* správa osob a letadel jen pro toho, kdo má právo (server ho hlídá také) */}
        {ja.prava.spravuje_osoby && (
          <NavLink className="nadpisek" to="/osoby">
            Osoby
          </NavLink>
        )}
        {ja.prava.spravuje_letadla && (
          <NavLink className="nadpisek" to="/letadla">
            Letadla
          </NavLink>
        )}
        <StitkyMenu jenCteni={ja.jen_cteni} />
      </nav>
    </>
  );
}

export function CasUtc() {
  const ted = useTik();
  return (
    <span>
      <span className="velke tucne cisla">{hodinyMinutySekundy(ted)}</span>{" "}
      <span className="male seda">UTC</span>
    </span>
  );
}

/** Upozornění vpravo v řádku menu (datum a sluneční časy v hlavičce tak zůstanou celé):
 *  letiště pro dnešek, je-li jiné než domovské (můj provoz; ťuknutí otevře výběr letiště),
 *  a přihlášení jen ke čtení (sdílený počítač). */
function StitkyMenu({ jenCteni }: { jenCteni: boolean }) {
  const den = useDen().data;
  const navigate = useNavigate();
  const jinde = den?.letiste && !den.letiste.domovske ? den.letiste : null;
  if (!jinde && !jenCteni) return null;
  return (
    <span className="menu-vpravo">
      {/* jen ke čtení: štítek letiště jen ukazuje (letiště pro dnešek nejde změnit) */}
      {jinde &&
        (jenCteni ? (
          <Stitek barva="oranzovy">{jinde.kod}</Stitek>
        ) : (
          <button
            type="button"
            className="menu-letiste"
            aria-label={`Letiště pro dnešek: ${jinde.kod} ${jinde.nazev}`}
            onClick={() => navigate("/muj-provoz/letiste")}
          >
            <Stitek barva="oranzovy">{jinde.kod}</Stitek>
          </button>
        ))}
      {jenCteni && <Stitek barva="oranzovy">Jen ke čtení</Stitek>}
    </span>
  );
}

/** Den a sluneční časy mého letiště pro dnešek (TB začátek a TE konec občanského soumraku). */
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

export function NabidkaUzivatele({ ja }: { ja: Ja }) {
  const [otevrena, setOtevrena] = useState(false);
  const navigate = useNavigate();
  const provoz = useMujProvoz().data;
  const letiste = provoz?.letiste;
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
          <div className="nabidka-oddil">
            <span className="tucne">
              {ja.jmeno} {ja.prijmeni}
            </span>
            <span className="male seda">{ja.email}</span>
            {ja.jen_cteni && (
              <span className="male">
                <Stitek barva="oranzovy">Jen ke čtení</Stitek> sdílený počítač – pro změny se
                odhlaste a přihlaste znovu
              </span>
            )}
          </div>
          {!ja.jen_cteni && (
            <div className="nabidka-oddil">
              <span className="nadpisek">Můj provoz · dnes</span>
              <Tlacitko
                varianta="bez-ramu"
                className="nabidka-polozka"
                onClick={() => navigate("/muj-provoz/letiste")}
              >
                Letiště
                <span className={letiste && !letiste.domovske ? "jinde" : undefined}>
                  {letiste ? `${letiste.kod} ${letiste.nazev}` : "—"}
                </span>
              </Tlacitko>
              <Tlacitko
                varianta="bez-ramu"
                className="nabidka-polozka"
                onClick={() => navigate("/muj-provoz/osoby")}
              >
                Osoby v provozu
                <span>{provoz?.osoby.length || "všechny"}</span>
              </Tlacitko>
            </div>
          )}
          <div className="nabidka-oddil">
            <span className="nadpisek">Režim zobrazení</span>
            <div className="segmenty">
              {REZIMY.map((r) => (
                <Tlacitko
                  key={r.rezim}
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
            </div>
          </div>
          <div className="nabidka-oddil">
            <Tlacitko
              varianta="bez-ramu"
              className="nabidka-polozka"
              disabled={odhlasit.isPending}
              onClick={() => odhlasit.mutate()}
            >
              Odhlásit
            </Tlacitko>
          </div>
        </div>
      )}
    </span>
  );
}
