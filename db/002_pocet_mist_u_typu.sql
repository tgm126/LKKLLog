-- 002: počet míst je vlastnost typu, ne letadla (3NF) – přesun z letadlo do lov_typ.
-- Hodnoty se převezmou z letadel; skript selže, pokud mají letadla jednoho typu různé počty.

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM lkkl.letadlo
        GROUP BY typ_id
        HAVING count(DISTINCT pocet_mist) > 1
    ) THEN
        RAISE EXCEPTION 'Letadla stejného typu mají různý počet míst – nejdřív sjednotit.';
    END IF;
END $$;

ALTER TABLE lkkl.lov_typ ADD COLUMN pocet_mist smallint CHECK (pocet_mist > 0);
COMMENT ON COLUMN lkkl.lov_typ.pocet_mist IS 'Počet míst včetně pilota; prázdné = nezadáno.';

UPDATE lkkl.lov_typ t
SET pocet_mist = l.pocet_mist
FROM (SELECT typ_id, max(pocet_mist) AS pocet_mist FROM lkkl.letadlo GROUP BY typ_id) l
WHERE l.typ_id = t.id;

DROP VIEW lkkl.v_letadlo;
ALTER TABLE lkkl.letadlo DROP COLUMN pocet_mist;

CREATE VIEW lkkl.v_letadlo AS
SELECT l.id,
       l.rejstrik,
       t.nazev AS typ,
       k.nazev AS kategorie,
       l.soukrome,
       t.pocet_mist,
       l.max_doba_min,
       l.vlecne
FROM lkkl.letadlo l
JOIN lkkl.lov_typ t       ON t.id = l.typ_id
JOIN lkkl.lov_kategorie k ON k.id = t.kategorie_id;
COMMENT ON VIEW lkkl.v_letadlo IS 'Letadla s názvem typu, kategorií a počtem míst (z typu).';
