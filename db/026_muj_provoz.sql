-- 026: můj provoz – letiště a osoby v provozu na dnešek, jen pro relaci (přihlášené zařízení)
-- (návrh docs/modul-muj-provoz.md). Nastavení platí jen pro den, kdy bylo uloženo (UTC, jako
-- přehled letů); jiný den se nebere v úvahu. Provozní tabulky bez auditu (nastavení zařízení,
-- místo letu se zapisuje do letu).

CREATE TABLE lkkl.relace_provoz (
    relace_id  text   PRIMARY KEY REFERENCES lkkl.relace,
    den        date   NOT NULL,
    letiste_id bigint REFERENCES lkkl.lov_letiste
);
COMMENT ON TABLE lkkl.relace_provoz IS 'Můj provoz: nastavení relace na jeden den (letiště, osoby v relace_provoz_osoba).';
COMMENT ON COLUMN lkkl.relace_provoz.den IS 'Den (UTC), pro který nastavení platí; jiný den se nebere v úvahu.';
COMMENT ON COLUMN lkkl.relace_provoz.letiste_id IS 'Letiště, kde dnes létám; prázdné = domovské.';
CREATE INDEX relace_provoz_letiste ON lkkl.relace_provoz (letiste_id);

CREATE TABLE lkkl.relace_provoz_osoba (
    relace_id text   NOT NULL REFERENCES lkkl.relace_provoz,
    osoba_id  bigint NOT NULL REFERENCES lkkl.lov_osoba,
    PRIMARY KEY (relace_id, osoba_id)
);
COMMENT ON TABLE lkkl.relace_provoz_osoba IS 'Osoby v provozu (filtr nabídky osob v posádce); žádný řádek = bez filtru.';
CREATE INDEX relace_provoz_osoba_osoba ON lkkl.relace_provoz_osoba (osoba_id);

-- Letiště relace pro dnešek: zvolené, jinak domovské (pravidlo „platí jen dnes“ jen tady).
CREATE VIEW lkkl.v_relace_letiste AS
SELECT r.id AS relace_id, l.id AS letiste_id, l.kod, l.nazev, l.zem_sirka, l.zem_delka,
       l.domovske
FROM lkkl.relace r
LEFT JOIN lkkl.relace_provoz rp ON rp.relace_id = r.id
                               AND rp.den = (now() AT TIME ZONE 'UTC')::date
JOIN lkkl.lov_letiste l ON l.id = coalesce(rp.letiste_id,
                                           (SELECT id FROM lkkl.lov_letiste WHERE domovske));
COMMENT ON VIEW lkkl.v_relace_letiste IS 'Dnešní letiště relace: zvolené v mém provozu, jinak domovské.';

-- Osoby v provozu relace pro dnešek.
CREATE VIEW lkkl.v_relace_osoba AS
SELECT ro.relace_id, ro.osoba_id
FROM lkkl.relace_provoz_osoba ro
JOIN lkkl.relace_provoz rp ON rp.relace_id = ro.relace_id
WHERE rp.den = (now() AT TIME ZONE 'UTC')::date;
COMMENT ON VIEW lkkl.v_relace_osoba IS 'Dnešní osoby v provozu relace (filtr nabídky osob).';
