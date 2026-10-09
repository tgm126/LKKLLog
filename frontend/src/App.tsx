import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Navigate, Outlet, Route, Routes, useLocation } from "react-router";

import { poslat, type Ja } from "./api";
import { Hlaska } from "./komponenty/Hlaska";
import { Hlavicka } from "./komponenty/Hlavicka";
import { OznameniProvider } from "./komponenty/Oznameni";
import { Pruh, PruhProvozu } from "./komponenty/Pruh";
import { Tlacitko } from "./komponenty/Tlacitko";
import { Vstupni } from "./komponenty/Vstupni";
import { Deska } from "./deska/Deska";
import { PanelDetailu } from "./deska/PanelDetailu";
import { PanelNovehoLetu } from "./deska/PanelNovehoLetu";
import { Detail } from "./lety/Detail";
import { Pruvodce } from "./lety/Pruvodce";
import { Detail as DetailOsoby } from "./osoby/Detail";
import { NovaOsoba } from "./osoby/Nova";
import { SeznamLetadel } from "./letadla/Seznam";
import { SeznamOsob } from "./osoby/Seznam";
import { LetisteProDnesek, OsobyVProvozu } from "./provoz/Provoz";
import { NastaveniSystemu, SmazatLetyDne } from "./sprava/Sprava";
import { EditorVycviku } from "./vycvik/Editor";
import { Lety } from "./stranky/Lety";
import { MojeLety } from "./stranky/MojeLety";
import { NastaveniHesla } from "./stranky/NastaveniHesla";
import { Prihlaseni } from "./stranky/Prihlaseni";
import { useDeska } from "./rozvrzeni";
import { useJa, useJenCteni, zmenitUzivatele } from "./uzivatel";

export function App() {
  // Provoz (přehled, detail letu, nový let): na desktopu provozní deska s panelem zprava,
  // jinak mobilní obrazovky (docs/modul-desktop.md). Adresy jsou stejné – odkaz funguje
  // na obou. Desktop je jedna stránka bez záložek: správa (osoby, letadla…) a můj provoz
  // z nabídky uživatele jako sloupec uprostřed (mobilní podoba).
  const deska = useDeska();
  return (
    <Routes>
      <Route path="/prihlaseni" element={<Prihlaseni />} />
      <Route path="/heslo" element={<NastaveniHesla />} />
      <Route element={<Prihlaseny />}>
        {deska ? (
          <Route path="/" element={<Deska />}>
            <Route index element={null} />
            <Route path="let/:id" element={<PanelDetailu />} />
            <Route element={<SeZapisem />}>
              <Route path="novy-let" element={<PanelNovehoLetu />} />
              <Route element={<SpravujeVycvik />}>
                <Route path="vycvik" element={<EditorVycviku />} />
              </Route>
            </Route>
          </Route>
        ) : (
          <>
            <Route element={<SHlavickou />}>
              <Route index element={<Lety />} />
              <Route path="/moje-lety" element={<MojeLety />} />
            </Route>
            <Route element={<SeZapisem />}>
              <Route path="/novy-let" element={<Pruvodce />} />
            </Route>
            <Route path="/let/:id" element={<Detail />} />
          </>
        )}
        {/* správa podle práv z nabídky uživatele; na počítači jako sloupec uprostřed */}
        <Route element={<SPravem pravo="spravuje_osoby" />}>
          <Route path="/osoby" element={<SeznamOsob />} />
          <Route path="/osoba/nova" element={<NovaOsoba />} />
          <Route path="/osoba/:id" element={<DetailOsoby />} />
        </Route>
        <Route element={<SPravem pravo="spravuje_letadla" />}>
          <Route path="/letadla" element={<SeznamLetadel />} />
        </Route>
        <Route element={<SeZapisem />}>
          <Route path="/muj-provoz/letiste" element={<LetisteProDnesek />} />
          <Route path="/muj-provoz/osoby" element={<OsobyVProvozu />} />
          <Route element={<JenAdmin />}>
            <Route path="/sprava/smazat-lety" element={<SmazatLetyDne />} />
            <Route path="/sprava/nastaveni" element={<NastaveniSystemu />} />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}

/** Rám obrazovek pro přihlášené; nepřihlášený jde na přihlášení a pak zpět, kam mířil. */
function Prihlaseny() {
  const { data: ja, error, refetch, isFetching } = useJa();
  const poloha = useLocation();
  if (ja === undefined) {
    if (!error) {
      return (
        <Vstupni nadpis="AK Kladno Log">
          <p className="seda" role="status">
            Načítám…
          </p>
        </Vstupni>
      );
    }
    return (
      <Vstupni nadpis="AK Kladno Log">
        <Hlaska>{error.message}</Hlaska>
        <Tlacitko varianta="obrys" disabled={isFetching} onClick={() => refetch()}>
          Zkusit znovu
        </Tlacitko>
      </Vstupni>
    );
  }
  if (ja === null) {
    const kam = poloha.pathname + poloha.search;
    const dalsi = kam === "/" ? "" : `?dalsi=${encodeURIComponent(kam)}`;
    return <Navigate to={`/prihlaseni${dalsi}`} replace />;
  }
  return (
    <OznameniProvider>
      <PruhProvozu />
      {ja.puvodni && <PruhJako ja={ja} />}
      <Outlet />
    </OznameniProvider>
  );
}

/** Obrazovky, které jen zapisují (nový let, můj provoz): v relaci jen ke čtení zpět na přehled. */
function SeZapisem() {
  return useJenCteni() ? <Navigate to="/" replace /> : <Outlet />;
}

/** Správa podle práva (osoby, letadla); server ho hlídá také. */
function SPravem({ pravo }: { pravo: keyof Ja["prava"] }) {
  return useJa().data?.prava[pravo] ? <Outlet /> : <Navigate to="/" replace />;
}

/** Správa systému jen pro admina (server ji hlídá také). */
function JenAdmin() {
  return useJa().data?.prava.admin ? <Outlet /> : <Navigate to="/" replace />;
}

/** Editor výcviku jen se správou výcviku (admin ji má vždy; server ji hlídá také). */
function SpravujeVycvik() {
  return useJa().data?.prava.spravuje_vycvik ? <Outlet /> : <Navigate to="/" replace />;
}

/** Obrazovky s hlavičkou a menu (průvodce a detail mají vlastní horní lištu). */
function SHlavickou() {
  const ja = useJa().data!;
  return (
    <>
      <Hlavicka ja={ja} />
      <Outlet />
    </>
  );
}

/** Admin přihlášený za jinou osobu vidí, za koho jedná, a může se vrátit. */
function PruhJako({ ja }: { ja: Ja }) {
  const qc = useQueryClient();
  const konec = useMutation({
    mutationFn: () => poslat<Ja>("/prihlasit-jako/konec"),
    onSuccess: (admin) => zmenitUzivatele(qc, admin),
  });
  return (
    <Pruh>
      Přihlášen jako {ja.jmeno} {ja.prijmeni}
      <Tlacitko disabled={konec.isPending} onClick={() => konec.mutate()}>
        Zpět na svůj účet
      </Tlacitko>
    </Pruh>
  );
}
