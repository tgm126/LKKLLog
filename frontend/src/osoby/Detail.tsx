import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate, useParams } from "react-router";

import { poslat, type Ja } from "../api";
import { datumCas } from "../cas";
import { Dialog } from "../komponenty/Dialog";
import { Hlaska } from "../komponenty/Hlaska";
import { Blok, BlokTelo, Obrazovka } from "../komponenty/Obrazovka";
import { Oznameni, useOznamit } from "../komponenty/Oznameni";
import { Pole } from "../komponenty/Pole";
import { Stitek } from "../komponenty/Stitek";
import { Tlacitko } from "../komponenty/Tlacitko";
import { Udaj, Udaje } from "../komponenty/Udaje";
import { Zaskrtavatka, Zaskrtavatko } from "../komponenty/Zaskrtavatko";
import { useJa, zmenitUzivatele } from "../uzivatel";
import {
  rozdelitNazev,
  telefonCitelne,
  useOsoba,
  useOsoby,
  useUpravitOsobu,
  type DetailOsoby,
  type Opravneni,
  type OpravneniOsoby,
  type UdajeOsoby,
} from "./api";
import "../komponenty/Volby.css";
import "./Osoby.css";

// Detail osoby (docs/modul-osoby.md, makety osoby-mobil.html a osoby-mobil-v2.html): údaje
// (ťuknutím upravit), člen a aktivní, účet a přihlášení, oprávnění po kategoriích letadel,
// historie změn.

export function Detail() {
  const id = Number(useParams().id);
  const { data: osoba, error } = useOsoba(id);
  const opravneni = useOsoby().data?.opravneni;
  const navigate = useNavigate();
  const zpet = () => navigate("/osoby");
  if (!osoba || !opravneni) {
    return (
      <Obrazovka zpet={zpet} zpetPopis="Zpět" nadpis="Osoba">
        {error && <Hlaska>{error.message}</Hlaska>}
      </Obrazovka>
    );
  }
  return <DetailObrazovka osoba={osoba} opravneni={opravneni} zpet={zpet} />;
}

/** Stav osoby a účtu do štítku v horní liště. */
function stav(o: DetailOsoby): [string, "zeleny" | "cerveny" | undefined] {
  if (!o.platny) return ["neaktivní", undefined];
  if (!o.ucet) return ["bez účtu", undefined];
  if (o.ucet.zablokovano) return ["zablokován", "cerveny"];
  return o.ucet.aktivni ? ["účet aktivní", "zeleny"] : ["účet vypnutý", undefined];
}

function DetailObrazovka({
  osoba: o,
  opravneni,
  zpet,
}: {
  osoba: DetailOsoby;
  opravneni: Opravneni[];
  zpet: () => void;
}) {
  const ja = useJa().data!;
  const [upravuji, setUpravuji] = useState<keyof UdajeOsoby | null>(null);
  const [historie, setHistorie] = useState(false);
  const upravit = useUpravitOsobu(o.id, () => setUpravuji(null));
  const zmenit = (zmeny: UdajeOsoby) => upravit.mutate({ cesta: `/osoby/${o.id}`, data: zmeny });
  const [text, barva] = stav(o);

  const pole = (klic: keyof UdajeOsoby, popisek: string, hodnota: string | null, cely = false) => (
    <Udaj
      popisek={popisek}
      hodnota={klic === "telefon" ? telefonCitelne(hodnota) : hodnota}
      cely={cely}
      upravit={() => setUpravuji(upravuji === klic ? null : klic)}
      otevreno={upravuji === klic}
    >
      <UpravaTextu
        popisek={popisek}
        puvodni={hodnota ?? ""}
        typ={klic === "email" ? "email" : klic === "telefon" ? "tel" : "text"}
        zrusit={() => setUpravuji(null)}
        ulozit={(novy) => zmenit({ [klic]: novy })}
      />
    </Udaj>
  );

  return (
    <Obrazovka
      zpet={zpet}
      zpetPopis="Zpět"
      nadpis={`${o.prijmeni} ${o.jmeno}`}
      vpravo={<Stitek barva={barva}>{text}</Stitek>}
    >
      <Blok nadpis="Osoba">
        <Udaje>
          {pole("jmeno", "Jméno", o.jmeno)}
          {pole("prijmeni", "Příjmení", o.prijmeni)}
          {pole("email", "E-mail", o.email, true)}
          {pole("telefon", "Telefon", o.telefon)}
          {pole("cislo_clena", "Číslo člena", o.cislo_clena)}
        </Udaje>
        <Zaskrtavatka>
          <Zaskrtavatko popisek="Člen klubu" zaskrtnuto={o.clen} zmenit={(clen) => zmenit({ clen })} />
          <Zaskrtavatko
            popisek="Aktivní"
            pod="nabízí se v letech, smí se přihlásit"
            zaskrtnuto={o.platny}
            zakazano={o.id === ja.osoba_id}
            zmenit={(platny) => zmenit({ platny })}
          />
        </Zaskrtavatka>
      </Blok>

      <BlokUctu osoba={o} ja={ja} />

      <Blok nadpis="Oprávnění" vpravo={`${o.opravneni.length} oprávnění`}>
        <div className="opravneni">
          {opravneni.map((p) => (
            <RadekOpravneni
              key={p.id}
              opravneni={p}
              osoby={o.opravneni.find((x) => x.id === p.id)}
              zmenit={(cesta, data) => upravit.mutate({ cesta: `/osoby/${o.id}/${cesta}`, data })}
            />
          ))}
        </div>
      </Blok>

      {o.historie.length > 0 && (
        <Blok nadpis="Historie změn">
          <Udaje>
            <Udaj
              popisek="Změny"
              hodnota={`${o.historie.length}`}
              cely
              upravit={() => setHistorie(!historie)}
              otevreno={historie}
            >
              {o.historie.map((h, i) => (
                <p key={i}>
                  <span className="cisla">{datumCas(h.kdy)}</span> · {h.akce} · {h.kdo}
                  {h.popis && <span className="udaj-pod">{h.popis}</span>}
                </p>
              ))}
            </Udaj>
          </Udaje>
        </Blok>
      )}
      <div className="oznameni-dole">
        <Oznameni />
      </div>
    </Obrazovka>
  );
}

/** Řádek oprávnění (maketa osoby-mobil-v2.html, varianta B): čipy kategorií letadel, pro které
 *  se smí vydat (zapnutá = osoba ho pro ni má), a u instruktorů, kteří ho mají, „omezený“. */
function RadekOpravneni({
  opravneni: p,
  osoby,
  zmenit,
}: {
  opravneni: Opravneni;
  osoby: OpravneniOsoby | undefined;
  zmenit: (cesta: "opravneni" | "omezeni", data: unknown) => void;
}) {
  const [zkratka, vysvetleni] = rozdelitNazev(p.nazev);
  return (
    <div
      role="group"
      aria-label={zkratka}
      className={osoby ? "opravneni-radek" : "opravneni-radek nema"}
    >
      <span>
        <span className="opravneni-zkratka">{zkratka}</span>
        {vysvetleni && <span className="male seda"> {vysvetleni}</span>}
      </span>
      <div className="cipy">
        {p.kategorie.map((k) => {
          const ma = !!osoby?.kategorie.includes(k.id);
          return (
            <Tlacitko
              key={k.id}
              aria-pressed={ma}
              onClick={() =>
                zmenit("opravneni", { opravneni_id: p.id, kategorie_id: k.id, ma: !ma })
              }
            >
              {k.nazev}
            </Tlacitko>
          );
        })}
        {osoby && p.lze_omezit && (
          <Tlacitko
            className="omezeny"
            aria-pressed={osoby.omezene}
            onClick={() => zmenit("omezeni", { opravneni_id: p.id, omezene: !osoby.omezene })}
          >
            omezený
          </Tlacitko>
        )}
      </div>
    </div>
  );
}

// --- účet a přihlášení -----------------------------------------------------------------------

function BlokUctu({ osoba: o, ja }: { osoba: DetailOsoby; ja: Ja }) {
  const upravit = useUpravitOsobu(o.id);
  const qc = useQueryClient();
  const navigate = useNavigate();
  const oznamit = useOznamit();
  const [odkaz, setOdkaz] = useState<string | null>(null);
  const u = o.ucet;
  const ucet = (data: Record<string, boolean>) =>
    upravit.mutate(
      u ? { cesta: `/ucty/${o.id}`, data } : { cesta: "/ucty", data: { osoba_id: o.id, ...data } },
    );
  // Admin má automaticky všechna práva: ostatní práva zaškrtnutá a zašedlá (uložená hodnota
  // platí, až admin přestane být adminem).
  const pravo = (
    klic: "admin" | "smi_odblokovat" | "spravuje_osoby" | "spravuje_letadla",
    popisek: string,
    pod?: string,
  ) => {
    const zAdmina = klic !== "admin" && !!u?.admin;
    return (
      <Zaskrtavatko
        popisek={popisek}
        pod={zAdmina ? "má jako admin" : pod}
        zaskrtnuto={zAdmina || !!u?.[klic]}
        zakazano={zAdmina || !u || !ja.prava.admin || (klic === "admin" && o.id === ja.osoba_id)}
        zmenit={(ano) => ucet({ [klic]: ano })}
      />
    );
  };

  const pozvanka = useMutation({
    mutationFn: () => poslat<{ odkaz: string }>(`/ucty/${o.id}/pozvanka`),
    onSuccess: (r) => {
      setOdkaz(r.odkaz);
      qc.invalidateQueries({ queryKey: ["osoba", o.id] });
    },
    onError: (e) => oznamit({ text: e.message, chyba: true }),
  });
  // Odkaz e-mailem z info@lkkl.cz – jen admin, s potvrzením adresy (docs/modul-email.md)
  const [potvrditEmail, setPotvrditEmail] = useState(false);
  const email = useMutation({
    mutationFn: () => poslat<{ adresa: string }>(`/ucty/${o.id}/pozvanka-emailem`),
    onSuccess: (r) => oznamit({ text: `Odkaz odeslán na ${r.adresa}` }),
    onError: (e) => oznamit({ text: e.message, chyba: true }),
    onSettled: () => {
      setPotvrditEmail(false);
      qc.invalidateQueries({ queryKey: ["osoba", o.id] });
    },
  });
  const jako = useMutation({
    mutationFn: () => poslat<Ja>(`/prihlasit-jako/${o.id}`),
    onSuccess: (novy) => {
      zmenitUzivatele(qc, novy);
      navigate("/");
    },
    onError: (e) => oznamit({ text: e.message, chyba: true }),
  });

  const info = [
    u && (u.ma_heslo ? `heslo nastaveno${o.heslo_zmeneno ? ` ${datumCas(o.heslo_zmeneno)}` : ""}` : "heslo nenastaveno"),
    o.pozvanka_odeslana && `odkaz ${datumCas(o.pozvanka_odeslana)}`,
    o.posledni_email &&
      (o.posledni_email.chyba
        ? `e-mail se nepodařilo odeslat ${datumCas(o.posledni_email.kdy)}`
        : `odkaz e-mailem ${datumCas(o.posledni_email.kdy)}`),
  ].filter(Boolean);

  return (
    <Blok
      nadpis="Účet a přihlášení"
      vpravo={o.posledni_prihlaseni && `naposledy ${datumCas(o.posledni_prihlaseni)}`}
    >
      <Zaskrtavatka>
        <Zaskrtavatko
          popisek="Smí se přihlásit"
          pod={!u ? "nemá účet (potřebuje e-mail)" : !o.platny ? "osoba je neaktivní" : undefined}
          zaskrtnuto={!!u?.aktivni}
          zakazano={o.id === ja.osoba_id || (u?.admin && !ja.prava.admin)}
          zmenit={(aktivni) => ucet({ aktivni })}
        />
        {pravo("admin", "Admin", "smí vše")}
        {pravo("spravuje_osoby", "Spravuje osoby")}
        {pravo("spravuje_letadla", "Spravuje letadla", "mimo provoz")}
        {pravo("smi_odblokovat", "Smí odblokovat", "po chybných heslech")}
        <Zaskrtavatko
          popisek="Zablokován"
          pod={u?.zablokovano ? "odškrtnutím odblokovat" : "není"}
          zaskrtnuto={!!u?.zablokovano}
          zakazano={!u?.zablokovano || !ja.prava.smi_odblokovat}
          zmenit={() => upravit.mutate({ cesta: `/ucty/${o.id}/odblokovat` })}
        />
      </Zaskrtavatka>
      {info.length > 0 && <div className="info-uctu male seda">{info.join(" · ")}</div>}
      {u && (
        <BlokTelo>
          <div className="akce-vedle">
            {ja.prava.admin && (
              <Tlacitko
                varianta="obrys"
                disabled={!u.smi_se_prihlasit || email.isPending}
                onClick={() => setPotvrditEmail(true)}
              >
                Odkaz e-mailem
              </Tlacitko>
            )}
            <Tlacitko
              varianta="obrys"
              disabled={!u.smi_se_prihlasit || pozvanka.isPending}
              onClick={() => pozvanka.mutate()}
            >
              Odkaz pro heslo
            </Tlacitko>
          </div>
          {ja.prava.admin && (
            <div className="akce-vedle">
              <Tlacitko
                varianta="obrys"
                disabled={!u.smi_se_prihlasit || u.admin || o.id === ja.osoba_id || jako.isPending}
                onClick={() => jako.mutate()}
              >
                Přihlásit se jako
              </Tlacitko>
            </div>
          )}
          {odkaz && <OdkazProHeslo odkaz={odkaz} />}
          {potvrditEmail && (
            <Dialog nadpis="Poslat odkaz e-mailem?" zavrit={() => setPotvrditEmail(false)}>
              <p>
                Odkaz pro nastavení hesla odejde z info@lkkl.cz na <b>{o.email}</b>. Platí 3 dny, po
                nastavení hesla už ne.
              </p>
              <Tlacitko varianta="modre" hlavni disabled={email.isPending} onClick={() => email.mutate()}>
                Poslat
              </Tlacitko>
              <Tlacitko varianta="obrys" onClick={() => setPotvrditEmail(false)}>
                Zpět
              </Tlacitko>
            </Dialog>
          )}
        </BlokTelo>
      )}
    </Blok>
  );
}

/** Odkaz pro nastavení hesla – správce ho zkopíruje a předá osobě sám (záloha k e-mailu). */
function OdkazProHeslo({ odkaz }: { odkaz: string }) {
  const [zkopirovano, setZkopirovano] = useState(false);
  return (
    <div className="odkaz-pro-heslo">
      <span className="male">{odkaz}</span>
      <Tlacitko
        varianta="svetle"
        onClick={() =>
          navigator.clipboard.writeText(odkaz).then(
            () => setZkopirovano(true),
            () => setZkopirovano(false),
          )
        }
      >
        {zkopirovano ? "Zkopírováno" : "Kopírovat"}
      </Tlacitko>
    </div>
  );
}

// --- úprava textového údaje -------------------------------------------------------------------

function UpravaTextu({
  popisek,
  puvodni,
  typ,
  zrusit,
  ulozit,
}: {
  popisek: string;
  puvodni: string;
  typ: "text" | "email" | "tel";
  zrusit: () => void;
  ulozit: (hodnota: string) => void;
}) {
  const [hodnota, setHodnota] = useState(puvodni);
  return (
    <form
      className="uprava-textu"
      onSubmit={(e) => {
        e.preventDefault();
        ulozit(hodnota);
      }}
    >
      <Pole popisek={popisek} type={typ} value={hodnota} onChange={(e) => setHodnota(e.target.value)} autoFocus />
      <div className="akce-vedle">
        <Tlacitko varianta="obrys" onClick={zrusit}>
          Zrušit
        </Tlacitko>
        <Tlacitko varianta="modre" type="submit" disabled={hodnota === puvodni}>
          Uložit
        </Tlacitko>
      </div>
    </form>
  );
}
