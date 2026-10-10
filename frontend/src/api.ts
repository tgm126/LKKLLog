// Volání rozhraní serveru (/api). Chyba serveru se převede na ChybaApi s hláškou pro člověka.
import type { components } from "./api.gen";

export class ChybaApi extends Error {
  readonly status: number;

  constructor(status: number, zprava: string) {
    super(zprava);
    this.status = status;
  }
}

const NEDOSTUPNY = "Server je nedostupný (možná se právě aktualizuje). Zkuste to za chvíli.";
// Na slabém signálu nesmí požadavek viset desítky sekund (tlačítko PŘISTÁL by zůstalo
// zašedlé): po limitu se ukončí a člověk ho zkusí znovu.
const LIMIT_S = 15;

async function zavolat<T>(metoda: "GET" | "POST", cesta: string, data?: unknown): Promise<T> {
  let odpoved: Response;
  try {
    odpoved = await fetch(`/api${cesta}`, {
      method: metoda,
      headers: data === undefined ? {} : { "Content-Type": "application/json" },
      body: data === undefined ? undefined : JSON.stringify(data),
      signal: AbortSignal.timeout(LIMIT_S * 1000),
    });
  } catch (e) {
    const vyprsel = e instanceof DOMException && e.name === "TimeoutError";
    throw new ChybaApi(
      0,
      vyprsel
        ? `Server neodpověděl do ${LIMIT_S} s. Zkuste to znovu.`
        : "Nepodařilo se spojit se serverem. Zkontrolujte připojení.",
    );
  }
  // Server neběží (nasazení, restart, výpadek) – odpovídá proxy před ním, ne aplikace.
  if ([502, 503, 504].includes(odpoved.status)) {
    throw new ChybaApi(odpoved.status, NEDOSTUPNY);
  }
  if (odpoved.status === 204) return undefined as T;
  const telo = await odpoved.json().catch(() => null);
  if (!odpoved.ok) {
    const detail = telo?.detail;
    throw new ChybaApi(
      odpoved.status,
      typeof detail === "string" ? detail : "Něco se nepovedlo. Zkuste to znovu.",
    );
  }
  return telo as T;
}

export const ziskat = <T>(cesta: string) => zavolat<T>("GET", cesta);
export const poslat = <T>(cesta: string, data?: unknown) => zavolat<T>("POST", cesta, data);

// --- typy odpovědí ---------------------------------------------------------------------------
// Generované z popisu rozhraní serveru (npm run api-typy → src/api.gen.ts); ručně se nepíší.

export type Schemata = components["schemas"];

export type OsobaKratce = Schemata["OsobaKratce"];
/** Přihlášený: jméno, e-mail, práva (včetně „admin smí vše“), skutečný admin při „přihlásit
 *  jako“, relace jen ke čtení. */
export type Ja = Schemata["Ja"];
export type Aplikace = Schemata["Aplikace"];
