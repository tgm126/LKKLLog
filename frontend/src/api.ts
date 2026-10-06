// Volání rozhraní serveru (/api). Chyba serveru se převede na ChybaApi s hláškou pro člověka.

export class ChybaApi extends Error {
  readonly status: number;

  constructor(status: number, zprava: string) {
    super(zprava);
    this.status = status;
  }
}

async function zavolat<T>(metoda: "GET" | "POST", cesta: string, data?: unknown): Promise<T> {
  let odpoved: Response;
  try {
    odpoved = await fetch(`/api${cesta}`, {
      method: metoda,
      headers: data === undefined ? {} : { "Content-Type": "application/json" },
      body: data === undefined ? undefined : JSON.stringify(data),
    });
  } catch {
    throw new ChybaApi(0, "Nepodařilo se spojit se serverem. Zkontrolujte připojení.");
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

export type OsobaKratce = { osoba_id: number; jmeno: string; prijmeni: string };

export type Ja = OsobaKratce & {
  email: string;
  prava: { admin: boolean; smi_odblokovat: boolean };
  /** Skutečný admin, pokud je přihlášen jako jiná osoba. */
  puvodni: OsobaKratce | null;
};

export type Aplikace = { verze: string; pruh: string };
