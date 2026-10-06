-- 010: pohledy pro nabídky – jen platné položky číselníků, seřazené podle pořadí a názvu.
-- Aplikace bere nabídky vždy odsud; vazby (cizí klíče) a stará data pracují s tabulkami,
-- takže zneplatněná položka u nich zůstane. Každý nový číselník dostane svůj v_lov_* pohled.

CREATE VIEW lkkl.v_lov_kategorie AS
SELECT id, kod, nazev, poradi
FROM lkkl.lov_kategorie WHERE platny ORDER BY poradi, nazev;

CREATE VIEW lkkl.v_lov_typ AS
SELECT id, kod, nazev, poradi, kategorie_id, pocet_mist
FROM lkkl.lov_typ WHERE platny ORDER BY poradi, nazev;

CREATE VIEW lkkl.v_lov_letiste AS
SELECT id, kod, nazev, poradi, domovske, zem_sirka, zem_delka, nadm_vyska_ft
FROM lkkl.lov_letiste WHERE platny ORDER BY domovske DESC, poradi, nazev;

CREATE VIEW lkkl.v_lov_ucel AS
SELECT id, kod, nazev, poradi
FROM lkkl.lov_ucel WHERE platny ORDER BY poradi, nazev;

CREATE VIEW lkkl.v_lov_zpusob_vzletu AS
SELECT id, kod, nazev, poradi
FROM lkkl.lov_zpusob_vzletu WHERE platny ORDER BY poradi, nazev;

CREATE VIEW lkkl.v_lov_funkce AS
SELECT id, kod, nazev, poradi, na_palube
FROM lkkl.lov_funkce WHERE platny ORDER BY poradi, nazev;

CREATE VIEW lkkl.v_lov_duvod_zruseni AS
SELECT id, kod, nazev, poradi
FROM lkkl.lov_duvod_zruseni WHERE platny ORDER BY poradi, nazev;

COMMENT ON VIEW lkkl.v_lov_kategorie IS 'Nabídka: platné kategorie.';
COMMENT ON VIEW lkkl.v_lov_typ IS 'Nabídka: platné typy letadel.';
COMMENT ON VIEW lkkl.v_lov_letiste IS 'Nabídka: platná letiště, domovské první.';
COMMENT ON VIEW lkkl.v_lov_ucel IS 'Nabídka: platné účely letu.';
COMMENT ON VIEW lkkl.v_lov_zpusob_vzletu IS 'Nabídka: platné způsoby vzletu.';
COMMENT ON VIEW lkkl.v_lov_funkce IS 'Nabídka: platné funkce v posádce.';
COMMENT ON VIEW lkkl.v_lov_duvod_zruseni IS 'Nabídka: platné důvody zrušení.';
