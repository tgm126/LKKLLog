import "./Sipka.css";

/** Šipka u času vzletu (šikmo nahoru ↗) a přistání (šikmo dolů ↘) – kreslená, aby byla na
 *  každém zařízení stejná a výraznější než znak písma. Barvu a velikost bere z textu. */
export function Sipka({ smer }: { smer: "vzlet" | "pristani" }) {
  return (
    <svg className="sipka" viewBox="0 0 24 24" role="img" aria-label={smer === "vzlet" ? "vzlet" : "přistání"}>
      <path d={smer === "vzlet" ? "M5 19L19 5M8 5h11v11" : "M5 5l14 14M19 8v11H8"} />
    </svg>
  );
}
