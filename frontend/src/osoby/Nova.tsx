import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router";

import { poslat } from "../api";
import { Hlaska } from "../komponenty/Hlaska";
import { Blok, BlokTelo, Obrazovka } from "../komponenty/Obrazovka";
import { Pole } from "../komponenty/Pole";
import { Tlacitko } from "../komponenty/Tlacitko";
import { Zaskrtavatka, Zaskrtavatko } from "../komponenty/Zaskrtavatko";
import type { DetailOsoby } from "./api";
import "./Osoby.css";

/** Nová osoba: údaje a Uložit → otevře se její detail (účet a oprávnění se nastaví tam). */
export function NovaOsoba() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [udaje, setUdaje] = useState({
    jmeno: "",
    prijmeni: "",
    email: "",
    telefon: "",
    cislo_clena: "",
  });
  const [clen, setClen] = useState(true);
  const ulozit = useMutation({
    mutationFn: () => poslat<DetailOsoby>("/osoby", { ...udaje, clen }),
    onSuccess: (o) => {
      qc.invalidateQueries({ queryKey: ["osoby"] });
      qc.setQueryData(["osoba", o.id], o);
      navigate(`/osoba/${o.id}`, { replace: true });
    },
  });
  const pole = (klic: keyof typeof udaje, popisek: string, typ = "text") => (
    <Pole
      popisek={popisek}
      type={typ}
      value={udaje[klic]}
      onChange={(e) => {
        const hodnota = e.target.value;
        setUdaje((u) => ({ ...u, [klic]: hodnota }));
      }}
    />
  );
  return (
    <Obrazovka
      zpet={() => navigate("/osoby")}
      zpetPopis="Zavřít"
      nadpis="Nová osoba"
      akce={
        <>
          <Hlaska>{ulozit.error?.message}</Hlaska>
          <Tlacitko
            varianta="modre"
            hlavni
            disabled={!udaje.jmeno.trim() || !udaje.prijmeni.trim() || ulozit.isPending}
            onClick={() => ulozit.mutate()}
          >
            Uložit
          </Tlacitko>
        </>
      }
    >
      <Blok nadpis="Osoba">
        <BlokTelo>
          {pole("jmeno", "Jméno")}
          {pole("prijmeni", "Příjmení")}
          {pole("email", "E-mail (potřeba pro přihlášení)", "email")}
          {pole("telefon", "Telefon", "tel")}
          {pole("cislo_clena", "Číslo člena")}
        </BlokTelo>
        <Zaskrtavatka>
          <Zaskrtavatko popisek="Člen klubu" pod="jinak externí" zaskrtnuto={clen} zmenit={setClen} />
        </Zaskrtavatka>
      </Blok>
    </Obrazovka>
  );
}
