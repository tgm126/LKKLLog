import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Navigate, Outlet, Route, Routes, useLocation } from "react-router";

import { poslat, type Ja } from "./api";
import { Hlaska } from "./komponenty/Hlaska";
import { Hlavicka } from "./komponenty/Hlavicka";
import { OznameniProvider } from "./komponenty/Oznameni";
import { Pruh, PruhProvozu } from "./komponenty/Pruh";
import { Tlacitko } from "./komponenty/Tlacitko";
import { Vstupni } from "./komponenty/Vstupni";
import { Detail } from "./lety/Detail";
import { Pruvodce } from "./lety/Pruvodce";
import { Detail as DetailOsoby } from "./osoby/Detail";
import { NovaOsoba } from "./osoby/Nova";
import { SeznamOsob } from "./osoby/Seznam";
import { LetisteProDnesek, OsobyVProvozu } from "./provoz/Provoz";
import { Lety } from "./stranky/Lety";
import { NastaveniHesla } from "./stranky/NastaveniHesla";
import { Prihlaseni } from "./stranky/Prihlaseni";
import { useJa, zmenitUzivatele } from "./uzivatel";

export function App() {
  return (
    <Routes>
      <Route path="/prihlaseni" element={<Prihlaseni />} />
      <Route path="/heslo" element={<NastaveniHesla />} />
      <Route element={<Prihlaseny />}>
        <Route element={<SHlavickou />}>
          <Route index element={<Lety />} />
          <Route path="/osoby" element={<SeznamOsob />} />
        </Route>
        <Route path="/novy-let" element={<Pruvodce />} />
        <Route path="/let/:id" element={<Detail />} />
        <Route path="/osoba/nova" element={<NovaOsoba />} />
        <Route path="/osoba/:id" element={<DetailOsoby />} />
        <Route path="/muj-provoz/letiste" element={<LetisteProDnesek />} />
        <Route path="/muj-provoz/osoby" element={<OsobyVProvozu />} />
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
    if (!error) return null;
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
