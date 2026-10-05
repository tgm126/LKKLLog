# Tabulky nové verze (schéma `lkkl`)

Průběžný seznam. Definice jsou v SQL skriptech `db/`; tabulky první verze viz
`tabulky-v1.md`.

| Objekt | Druh | Účel | Skript |
|---|---|---|---|
| `lov_kategorie` | číselník | kategorie letadel | 001 |
| `lov_typ` | číselník | typy letadel → kategorie, počet míst | 001, 002 |
| `letadlo` | tabulka | letadla: rejstříková značka, typ, soukromé, max. doba letu, vlečné | 001, 002 |
| `v_letadlo` | pohled | letadla s názvem typu, kategorií a počtem míst | 001, 002 |
| `lov_letiste` | číselník | česká letiště s kódem ICAO, název, domovské (nejvýš jedno), souřadnice, nadmořská výška [ft] | 003 |
| `osoba` | tabulka | osoby: jméno, příjmení, e-mail (jedinečný bez ohledu na velikost písmen), telefon (+420…), číslo člena (text, jen u členů), člen / externí, aktivní | 004 |

## Rozhodnutí pro další tabulky

- **Hosté** se neevidují jménem: u letu se eviduje PIC a počet osob na palubě (POB).
- **Přistání do terénu** není letiště: u letu cizí klíč na letiště, nebo popis místa (právě jedno).
- **Aktivace v aplikaci** = založení přihlašovacího účtu (tabulka `ucet`, 1:0..1 k osobě);
  osoby se aktivují postupně (fáze 2 testování: vybraní pilotní uživatelé).
- **Role v aplikaci** jako číselník `lov_role` + vazba osoba–role, ne sloupce osoby.
- Datum narození se neeviduje (sloupec jde kdykoli přidat).

**Záloha** lokálních dat: `bash db/zaloha.sh` → `C:\GIT\LKKLLog-zalohy` (mimo git; obnova
je popsaná v hlavičce skriptu).
