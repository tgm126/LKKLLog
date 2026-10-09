import { describe, expect, it } from "vitest";

import { datumCas, denSlovy, doba, hodinyMinuty, hodinyMinutySekundy, stopky } from "./cas";

describe("čas (UTC)", () => {
  it("hodiny a minuty z ISO i z Date", () => {
    expect(hodinyMinuty("2026-10-09T14:05:09Z")).toBe("14:05");
    expect(hodinyMinuty(new Date("2026-10-09T03:07:00Z"))).toBe("03:07");
    expect(hodinyMinutySekundy(new Date("2026-10-09T14:05:09Z"))).toBe("14:05:09");
  });

  it("stopky letu od vzletu, nikdy záporné", () => {
    expect(stopky("2026-10-09T14:05:09Z", new Date("2026-10-09T15:17:43Z"))).toBe("1:12:34");
    expect(stopky("2026-10-09T14:05:09Z", new Date("2026-10-09T14:05:09Z"))).toBe("0:00:00");
    expect(stopky("2026-10-09T14:05:09Z", new Date("2026-10-09T14:00:00Z"))).toBe("0:00:00");
  });

  it("doba leteckým zápisem", () => {
    expect(doba(0)).toBe('0"');
    expect(doba(45)).toBe('45"');
    expect(doba(60)).toBe('1°00"');
    expect(doba(62)).toBe('1°02"');
  });

  it("datum s časem a den slovy", () => {
    expect(datumCas("2026-10-06T21:14:00Z")).toBe("6. 10. 21:14");
    expect(denSlovy("2026-10-06")).toBe("Úterý 6. 10. 2026");
  });
});
