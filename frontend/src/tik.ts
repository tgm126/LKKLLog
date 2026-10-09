// Překreslení každou sekundu (hodiny, stopky letu) podle času serveru. Jeden časovač pro
// všechny (na desce tiká i patnáct pásků najednou): stopky sousedních pásků skáčou ve stejnou
// chvíli, ne každé s jinou fází (code review 9. 10. 2026, F9).
import { useEffect, useState } from "react";

import { ted } from "./cas";

const posluchaci = new Set<() => void>();
let casovac: ReturnType<typeof setInterval> | undefined;

function pripojit(posluchac: () => void): () => void {
  posluchaci.add(posluchac);
  casovac ??= setInterval(() => posluchaci.forEach((p) => p()), 1000);
  return () => {
    posluchaci.delete(posluchac);
    if (posluchaci.size === 0 && casovac !== undefined) {
      clearInterval(casovac);
      casovac = undefined;
    }
  };
}

export function useTik(): Date {
  const [cas, setCas] = useState(ted);
  useEffect(() => pripojit(() => setCas(ted())), []);
  return cas;
}
