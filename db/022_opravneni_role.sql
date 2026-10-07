-- 022: oprávnění ↔ role v letu místo pevných příznaků vycvik / prezkousi / vleka (021).
-- Role = účel letu + funkce osoby (výcvik · PIC, sólo · dozor, přezkoušení · PIC; vlečný let
-- je let bez účelu · PIC). Jedno oprávnění opravňuje k více rolím a jednu roli zastanou různá
-- oprávnění (FE vede i výcvik, FI dělá i přezkoušení) – vše v datech, program nic neví
-- o instruktorech ani vlecích. Nabídka osob v průvodci podle role a kategorie letadla.

CREATE TABLE lkkl.lov_opravneni_role (
    id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    opravneni_id bigint NOT NULL REFERENCES lkkl.lov_opravneni,
    ucel_id      bigint REFERENCES lkkl.lov_ucel,
    funkce_id    bigint NOT NULL REFERENCES lkkl.lov_funkce,
    UNIQUE NULLS NOT DISTINCT (opravneni_id, ucel_id, funkce_id)
);
COMMENT ON TABLE lkkl.lov_opravneni_role IS 'K jakým rolím v letu (účel + funkce) oprávnění opravňuje – nabídka osob v posádce.';
COMMENT ON COLUMN lkkl.lov_opravneni_role.ucel_id IS 'Účel letu; prázdný = vlečný let (jako let.ucel_id).';
CREATE INDEX lov_opravneni_role_ucel ON lkkl.lov_opravneni_role (ucel_id);
CREATE INDEX lov_opravneni_role_funkce ON lkkl.lov_opravneni_role (funkce_id);

-- Převod příznaků na role (výchozí naplnění, správce ho upraví): kdo smí vést výcvik nebo
-- přezkoušet → výcvik · PIC, sólo · dozor, přezkoušení · PIC; vlekař → vlečný let · PIC.
INSERT INTO lkkl.lov_opravneni_role (opravneni_id, ucel_id, funkce_id)
SELECT o.id, u.id, f.id
FROM lkkl.lov_opravneni o
JOIN (VALUES ('VYCVIK', 'PIC'), ('VYCVIK_SOLO', 'DOZOR'), ('PREZKOUSENI', 'PIC')) AS r(ucel, funkce)
    ON o.vycvik OR o.prezkousi
JOIN lkkl.lov_ucel u   ON u.kod = r.ucel
JOIN lkkl.lov_funkce f ON f.kod = r.funkce;
INSERT INTO lkkl.lov_opravneni_role (opravneni_id, ucel_id, funkce_id)
SELECT o.id, NULL, f.id
FROM lkkl.lov_opravneni o JOIN lkkl.lov_funkce f ON f.kod = 'PIC'
WHERE o.vleka;

-- Příznaky pryč (pohledy nad nimi se založí znovu).
DROP VIEW lkkl.v_osoba_smi;
DROP VIEW lkkl.v_lov_opravneni;
ALTER TABLE lkkl.lov_opravneni DROP COLUMN vycvik, DROP COLUMN prezkousi, DROP COLUMN vleka;

CREATE VIEW lkkl.v_lov_opravneni AS
SELECT * FROM lkkl.lov_opravneni WHERE platny ORDER BY poradi, nazev;

CREATE VIEW lkkl.v_osoba_smi AS
SELECT DISTINCT oo.osoba_id, u.kod AS ucel_kod, f.kod AS funkce_kod, k.kod AS kategorie_kod
FROM lkkl.lov_osoba_opravneni oo
JOIN lkkl.lov_opravneni o                 ON o.id = oo.opravneni_id AND o.platny
JOIN lkkl.lov_opravneni_role r            ON r.opravneni_id = o.id
LEFT JOIN lkkl.lov_ucel u                 ON u.id = r.ucel_id
JOIN lkkl.lov_funkce f                    ON f.id = r.funkce_id
LEFT JOIN lkkl.lov_opravneni_kategorie ok ON ok.opravneni_id = o.id
LEFT JOIN lkkl.lov_kategorie k            ON k.id = ok.kategorie_id;
COMMENT ON VIEW lkkl.v_osoba_smi IS 'Role, které osoba smí zastat: účel (prázdný = vlečný let), funkce, kategorie letadla (prázdná = všechny).';
