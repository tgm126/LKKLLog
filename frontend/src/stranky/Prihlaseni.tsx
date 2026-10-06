import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router";

import { poslat, type Ja } from "../api";
import { Hlaska } from "../komponenty/Hlaska";
import { Pole } from "../komponenty/Pole";
import { Tlacitko } from "../komponenty/Tlacitko";
import { Vstupni } from "../komponenty/Vstupni";
import { adresaPoPrihlaseni, useJa, zmenitUzivatele } from "../uzivatel";

export function Prihlaseni() {
  const ja = useJa().data;
  const [parametry] = useSearchParams();
  const kam = adresaPoPrihlaseni(parametry.get("dalsi"));
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [email, setEmail] = useState("");
  const [heslo, setHeslo] = useState("");
  const poleHeslo = useRef<HTMLInputElement>(null);

  const prihlasit = useMutation({
    mutationFn: () => poslat<Ja>("/prihlaseni", { email, heslo }),
    onSuccess: (prihlaseny) => {
      zmenitUzivatele(qc, prihlaseny);
      navigate(kam, { replace: true });
    },
    onError: () => {
      setHeslo("");
      poleHeslo.current?.focus();
    },
  });

  if (ja && !prihlasit.isSuccess) return <Navigate to={kam} replace />;

  return (
    <Vstupni nadpis="AK Kladno Log" podnadpis="Evidence letů">
      <form
        className="formular"
        noValidate
        onSubmit={(e) => {
          e.preventDefault();
          if (!prihlasit.isPending) prihlasit.mutate();
        }}
      >
        <Pole
          popisek="E-mail"
          type="email"
          autoComplete="username"
          inputMode="email"
          autoCapitalize="off"
          spellCheck={false}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <Pole
          popisek="Heslo"
          type="password"
          autoComplete="current-password"
          ukazat
          ref={poleHeslo}
          value={heslo}
          onChange={(e) => setHeslo(e.target.value)}
        />
        <Hlaska>{prihlasit.error?.message}</Hlaska>
        <Tlacitko type="submit" varianta="modre" hlavni disabled={prihlasit.isPending}>
          {prihlasit.isPending ? "Přihlašuji…" : "Přihlásit"}
        </Tlacitko>
        <p className="male seda">
          První přihlášení nebo zapomenuté heslo: odkaz pro nastavení hesla vám dá správce
          aplikace.
        </p>
      </form>
    </Vstupni>
  );
}
