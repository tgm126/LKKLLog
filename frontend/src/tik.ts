// Překreslení každou sekundu (hodiny, stopky letu) podle času serveru.
import { useEffect, useState } from "react";

import { ted } from "./cas";

export function useTik(): Date {
  const [cas, setCas] = useState(ted);
  useEffect(() => {
    const casovac = setInterval(() => setCas(ted()), 1000);
    return () => clearInterval(casovac);
  }, []);
  return cas;
}
