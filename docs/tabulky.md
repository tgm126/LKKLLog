# Tabulky nové verze (schéma `lkkl`)

Průběžný seznam. Definice jsou v SQL skriptech `db/`; tabulky první verze viz
`tabulky-v1.md`.

| Objekt | Druh | Účel | Skript |
|---|---|---|---|
| `lov_kategorie` | číselník | kategorie letadel | 001 |
| `lov_typ` | číselník | typy letadel → kategorie, počet míst | 001, 002 |
| `letadlo` | tabulka | letadla: rejstříková značka, typ, soukromé, max. doba letu, vlečné | 001, 002 |
| `v_letadlo` | pohled | letadla s názvem typu, kategorií a počtem míst | 001, 002 |

**Záloha** lokálních dat: `bash db/zaloha.sh` → `C:\GIT\LKKLLog-zalohy` (mimo git; obnova
je popsaná v hlavičce skriptu).
