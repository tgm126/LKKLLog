# Tabulky nové verze (schéma `lkkl`)

Průběžný seznam. Definice jsou v SQL skriptech `db/`; tabulky první verze viz
`tabulky-v1.md`.

| Objekt | Druh | Účel | Skript |
|---|---|---|---|
| `lov_kategorie` | číselník | kategorie letadel | 001 |
| `lov_typ` | číselník | typy letadel → kategorie | 001 |
| `letadlo` | tabulka | letadla: rejstříková značka, typ, soukromé, počet míst, max. doba letu, vlečné | 001 |
| `v_letadlo` | pohled | letadla s názvem typu a kategorií | 001 |
