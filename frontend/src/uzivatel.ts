// Kdo je přihlášen a údaje aplikace (verze, pruh) – sdílené dotazy pro všechny obrazovky.
import { useQuery, type QueryClient } from "@tanstack/react-query";

import { ChybaApi, ziskat, type Aplikace, type Ja } from "./api";

export const KLIC_JA = ["ja"] as const;

/** Přihlášený uživatel (`data`): `null` = nepřihlášen, `undefined` = zatím se zjišťuje
 *  nebo server není dostupný (`error`). */
export function useJa() {
  return useQuery({
    queryKey: KLIC_JA,
    queryFn: async () => {
      try {
        return await ziskat<Ja>("/ja");
      } catch (e) {
        if (e instanceof ChybaApi && e.status === 401) return null;
        throw e;
      }
    },
    staleTime: Infinity,
  });
}

/** Přihlášeno jen ke čtení (sdílený počítač): aplikace skryje všechno ovládání se zápisem
 *  (zápisy hlídá server). */
export const useJenCteni = () => useJa().data?.jen_cteni ?? false;

/** Přihlášení, odhlášení, „přihlásit se jako“: nový uživatel a zahodit data předchozího. */
export function zmenitUzivatele(qc: QueryClient, ja: Ja | null): void {
  qc.removeQueries({ predicate: (q) => !["ja", "aplikace"].includes(String(q.queryKey[0])) });
  qc.setQueryData(KLIC_JA, ja);
}

// Verze serveru při načtení stránky: když se po nasazení změní, otevřená aplikace (běží
// třeba celý den v telefonu) nabídne načtení nové verze.
let verzePriNacteni: string | undefined;

export function useAplikace() {
  return useQuery({
    queryKey: ["aplikace"],
    queryFn: async () => {
      const aplikace = await ziskat<Aplikace>("/aplikace");
      verzePriNacteni ??= aplikace.verze;
      return { ...aplikace, novaVerze: aplikace.verze !== verzePriNacteni };
    },
    refetchInterval: 60_000,
  }).data;
}

/** Kam po přihlášení: jen adresa v rámci aplikace (ne cizí web podstrčený v odkazu). */
export function adresaPoPrihlaseni(dalsi: string | null): string {
  return dalsi?.startsWith("/") && !dalsi.startsWith("//") ? dalsi : "/";
}

export function inicialy(osoba: { jmeno: string; prijmeni: string }): string {
  return `${osoba.jmeno.charAt(0)}${osoba.prijmeni.charAt(0)}`.toUpperCase();
}
