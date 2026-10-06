-- 018: osoba na palubě nemůže být ve vzduchu ve dvou letech zároveň.
--
-- Kontroluje se při vzletu, přistání, proběhlém letu, úpravě časů, posádce i obnovení letu
-- (odložená kontrola letu na konci transakce). Plánování je volné (naplánovaný let nemá čas);
-- dozor na zemi (funkce bez příznaku na_palube) se nepočítá. Let ve vzduchu trvá do přistání.

CREATE FUNCTION lkkl.let_osoby_bez_prekryvu(p_let_id bigint) RETURNS void LANGUAGE plpgsql AS $$
DECLARE
    r record;
BEGIN
    SELECT o.jmeno || ' ' || o.prijmeni AS osoba, a.rejstrik
    INTO r
    FROM lkkl.let l
    JOIN lkkl.posadka p ON p.let_id = l.id
    JOIN lkkl.lov_funkce f ON f.id = p.funkce_id AND f.na_palube
    JOIN lkkl.posadka p2 ON p2.osoba_id = p.osoba_id AND p2.let_id <> l.id
    JOIN lkkl.lov_funkce f2 ON f2.id = p2.funkce_id AND f2.na_palube
    JOIN lkkl.let l2 ON l2.id = p2.let_id
    JOIN lkkl.lov_letadlo a ON a.id = l2.letadlo_id
    JOIN lkkl.lov_osoba o ON o.id = p.osoba_id
    WHERE l.id = p_let_id
      AND l.cas_vzletu IS NOT NULL AND l.zruseni_duvod_id IS NULL
      AND l2.cas_vzletu IS NOT NULL AND l2.zruseni_duvod_id IS NULL
      -- bez přistání = ve vzduchu (rozsah bez horní meze); přistání a vzlet ve stejnou chvíli jde
      AND tstzrange(l.cas_vzletu, l.cas_pristani) && tstzrange(l2.cas_vzletu, l2.cas_pristani)
    LIMIT 1;
    IF FOUND THEN
        RAISE EXCEPTION 'Let %: % je v tu dobu na palubě jiného letu (%).', p_let_id, r.osoba, r.rejstrik;
    END IF;
END $$;
COMMENT ON FUNCTION lkkl.let_osoby_bez_prekryvu(bigint) IS
    'Osoba na palubě (PIC, žák, přezkoušený) nesmí být ve vzduchu ve dvou letech zároveň.';

CREATE OR REPLACE FUNCTION lkkl.let_kontrola() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_TABLE_NAME = 'let' THEN
        PERFORM lkkl.let_zkontrolovat(NEW.id);
        PERFORM lkkl.let_osoby_bez_prekryvu(NEW.id);
        -- Změna vazby na vlečný let mění i to, zda je vlečný let „vlek“.
        IF TG_OP = 'UPDATE' AND OLD.vlecny_let_id IS DISTINCT FROM NEW.vlecny_let_id THEN
            PERFORM lkkl.let_zkontrolovat(OLD.vlecny_let_id);
        END IF;
        PERFORM lkkl.let_zkontrolovat(NEW.vlecny_let_id);
    ELSE
        IF TG_OP IN ('UPDATE', 'DELETE') THEN
            PERFORM lkkl.let_zkontrolovat(OLD.let_id);
        END IF;
        IF TG_OP IN ('INSERT', 'UPDATE') THEN
            PERFORM lkkl.let_zkontrolovat(NEW.let_id);
            PERFORM lkkl.let_osoby_bez_prekryvu(NEW.let_id);
        END IF;
    END IF;
    RETURN NULL;
END $$;
