import "./Sipka.css";

const SIPKY = {
  vzlet: { popis: "vzlet", cara: "M5 19L19 5M8 5h11v11" },
  pristani: { popis: "přistání", cara: "M5 5l14 14M19 8v11H8" },
  kam: { popis: "do", cara: "M3 12h17M13 5l7 7-7 7" },
};

/** Šipka u času vzletu (šikmo nahoru ↗), přistání (šikmo dolů ↘) a v trase odkud → kam –
 *  kreslená, aby byla na každém zařízení stejná a výraznější než znak písma. Barvu
 *  a velikost bere z textu. */
export function Sipka({ smer }: { smer: keyof typeof SIPKY }) {
  return (
    <svg className="sipka" viewBox="0 0 24 24" role="img" aria-label={SIPKY[smer].popis}>
      <path d={SIPKY[smer].cara} />
    </svg>
  );
}
