-- 027: místo vzletu i přistání má každý let od založení (docs/modul-lety.md, rozhodnutí 8).
-- Do přistání je místo přistání plán (cíl), po přistání skutečnost; jde upravit kdykoli.
-- Nezadané místo = výchozí letiště – aplikace posílá moje letiště (můj provoz), databáze
-- doplní domovské (zápis přímo v databázi). Dosud se místo přistání doplňovalo až při přistání.

-- Stávající lety bez místa přistání (naplánované, ve vzduchu, zrušené před přistáním) dostanou
-- domovské letiště – stejně, jako by se doplnilo při přistání. Převod, ne úprava uživatelem:
-- do historie letu se nezapisuje.
ALTER TABLE lkkl.let DISABLE TRIGGER audit;
UPDATE lkkl.let
SET misto_pristani_id = (SELECT id FROM lkkl.lov_letiste WHERE domovske)
WHERE misto_pristani_id IS NULL AND misto_pristani_popis IS NULL;
ALTER TABLE lkkl.let ENABLE TRIGGER audit;

-- Místo přistání vždy (letiště, nebo popis); počet přistání dál jen po přistání.
ALTER TABLE lkkl.let
    DROP CONSTRAINT pristani_ma_misto_a_pocet,
    DROP CONSTRAINT misto_pristani_nejvys_jedno,
    ADD CONSTRAINT misto_pristani_jedno
        CHECK ((misto_pristani_id IS NULL) <> (misto_pristani_popis IS NULL)),
    ADD CONSTRAINT pocet_pristani_po_pristani
        CHECK ((cas_pristani IS NULL AND pocet_pristani IS NULL)
               OR (cas_pristani IS NOT NULL AND pocet_pristani >= 1));
COMMENT ON COLUMN lkkl.let.misto_pristani_id IS
    'Místo přistání (letiště); do přistání plán (cíl), po přistání skutečnost.';

-- Nezadané místo vzletu i přistání = domovské letiště (pojistka pro zápis přímo v databázi).
CREATE OR REPLACE FUNCTION lkkl.let_doplnit_misto() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    v_domovske bigint := (SELECT id FROM lkkl.lov_letiste WHERE domovske);
BEGIN
    IF NEW.misto_vzletu_id IS NULL AND NEW.misto_vzletu_popis IS NULL THEN
        NEW.misto_vzletu_id := v_domovske;
    END IF;
    IF NEW.misto_pristani_id IS NULL AND NEW.misto_pristani_popis IS NULL THEN
        NEW.misto_pristani_id := v_domovske;
    END IF;
    RETURN NEW;
END $$;
