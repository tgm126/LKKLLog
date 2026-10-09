import { describe, expect, it } from "vitest";

import type { Pasek } from "./api";
import { dvojice, podle } from "./poradi";

/** Jen údaje, které řazení a dvojice používají. */
const let_ = (id: number, vlecny_let_id: number | null = null, cas_vzletu: string | null = null) =>
  ({ id, vlecny_let_id, cas_vzletu }) as Pasek;

describe("pořadí letů", () => {
  it("řadí podle času, prázdný čas první; sestupně obráceně", () => {
    const lety = [let_(1, null, "10:05"), let_(2), let_(3, null, "09:30")];
    expect(lety.sort(podle((l) => l.cas_vzletu)).map((l) => l.id)).toEqual([2, 3, 1]);
    expect(lety.sort(podle((l) => l.cas_vzletu, true)).map((l) => l.id)).toEqual([1, 3, 2]);
  });

  it("vlek je dvojice kluzák + vlečná; vlečná bez kluzáku v seznamu zůstane sama", () => {
    const kluzak = let_(1, 2);
    const vlecna = let_(2);
    const samotna = let_(3);
    expect(dvojice([vlecna, kluzak, samotna])).toEqual([[kluzak, vlecna], [samotna]]);
    expect(dvojice([let_(4, 99)])).toEqual([[let_(4, 99)]]);
  });
});
