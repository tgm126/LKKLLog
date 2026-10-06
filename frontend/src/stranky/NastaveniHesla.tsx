import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router";

import { poslat, ziskat, type Ja, type OsobaKratce } from "../api";
import { Hlaska } from "../komponenty/Hlaska";
import { Pole } from "../komponenty/Pole";
import { Tlacitko } from "../komponenty/Tlacitko";
import { Vstupni } from "../komponenty/Vstupni";
import { zmenitUzivatele } from "../uzivatel";

// Stejné meze jako na serveru (docs/modul-prihlasovani.md, 4.5).
const MIN = 10;
const MAX = 128;
const NEPLATNY_ODKAZ = "Odkaz neplatí nebo vypršel. Požádejte admina o nový.";

function napoveda(delka: number): string {
  if (delka === 0) {
    return `${MIN} až ${MAX} znaků. Delší heslo je bezpečnější než složité – třeba několik slov.`;
  }
  if (delka > MAX) return `Nejvýš ${MAX} znaků.`;
  const zbyva = MIN - delka;
  if (zbyva <= 0) return `${delka} znaků – v pořádku.`;
  return `Ještě ${zbyva} ${zbyva === 1 ? "znak" : zbyva < 5 ? "znaky" : "znaků"}.`;
}

/** Nastavení hesla odkazem od admina (/heslo?klic=…); po uložení rovnou přihlášen. */
export function NastaveniHesla() {
  const [parametry] = useSearchParams();
  const klic = parametry.get("klic") ?? "";
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [heslo, setHeslo] = useState("");

  const odkaz = useQuery({
    queryKey: ["odkaz", klic],
    queryFn: () =>
      ziskat<OsobaKratce & { email: string }>(`/heslo/odkaz?klic=${encodeURIComponent(klic)}`),
    enabled: klic !== "",
    retry: false,
    staleTime: Infinity,
  });
  const ulozit = useMutation({
    mutationFn: () => poslat<Ja>("/heslo/nastavit", { klic, heslo }),
    onSuccess: (ja) => {
      zmenitUzivatele(qc, ja);
      navigate("/", { replace: true });
    },
  });

  if (klic !== "" && odkaz.isPending) return <Vstupni nadpis="Nastavení hesla">{null}</Vstupni>;

  const osoba = odkaz.data;
  if (!osoba) {
    return (
      <Vstupni nadpis="Nastavení hesla">
        <Hlaska>{odkaz.error?.message ?? NEPLATNY_ODKAZ}</Hlaska>
        <Tlacitko varianta="obrys" onClick={() => navigate("/prihlaseni", { replace: true })}>
          Na přihlášení
        </Tlacitko>
      </Vstupni>
    );
  }

  const delka = [...heslo].length;
  return (
    <Vstupni nadpis="Nastavení hesla" podnadpis={`${osoba.jmeno} ${osoba.prijmeni}`}>
      <form
        className="formular"
        noValidate
        onSubmit={(e) => {
          e.preventDefault();
          if (!ulozit.isPending) ulozit.mutate();
        }}
      >
        {/* Pro správce hesel: uloží nové heslo ke správnému e-mailu. */}
        <input type="email" autoComplete="username" value={osoba.email} readOnly hidden />
        <Pole
          popisek="Nové heslo"
          type="password"
          autoComplete="new-password"
          ukazat
          value={heslo}
          onChange={(e) => setHeslo(e.target.value)}
          napoveda={napoveda(delka)}
        />
        <Hlaska>{ulozit.error?.message}</Hlaska>
        <Tlacitko
          type="submit"
          varianta="modre"
          hlavni
          disabled={delka < MIN || delka > MAX || ulozit.isPending}
        >
          {ulozit.isPending ? "Ukládám…" : "Uložit a přihlásit"}
        </Tlacitko>
        <p className="male seda">Po uložení se odhlásí ostatní zařízení a odkaz přestane platit.</p>
      </form>
    </Vstupni>
  );
}
