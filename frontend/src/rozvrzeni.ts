// Desktop, nebo mobil – podle šířky okna, ne podle zařízení (docs/modul-desktop.md, kap. 2):
// od 1200 px provozní deska, od 1500 px navíc pravý sloupec souhrnů. Přepne se i při změně
// velikosti okna. Hranice jsou tady (ne v CSS), protože pevné rozměry patří jen do tokenů
// a rozvržení vybírá komponenty, ne jen styly.
import { useSyncExternalStore } from "react";

const DESKA = "(min-width: 1200px)";
const SIROKA = "(min-width: 1500px)";

function useMedia(dotaz: string): boolean {
  return useSyncExternalStore(
    (zmena) => {
      const m = matchMedia(dotaz);
      m.addEventListener("change", zmena);
      return () => m.removeEventListener("change", zmena);
    },
    () => matchMedia(dotaz).matches,
  );
}

/** Provozní deska pro myš (jinak mobilní obrazovky). */
export const useDeska = () => useMedia(DESKA);

/** Deska s pravým sloupcem souhrnů (užší ho má za tlačítkem v liště). */
export const useSirokaDeska = () => useMedia(SIROKA);
