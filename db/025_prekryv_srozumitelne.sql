-- 025: srozumitelná hláška, když letadlo nebo osoba v tu dobu letí jinde – s konkrétními údaji
-- druhého letu (rejstřík, čas vzletu / doba letu, PIC). Omezení letadlo_bez_prekryvu (009)
-- zůstává jako pojistka pro souběh dvou současných změn (pak obecná hláška ze serveru).

-- Čas pro hlášku v UTC: dnes jen „10:42“, jiný den „6. 10. 10:42“.
CREATE FUNCTION lkkl.cas_hlasky(p_cas timestamptz) RETURNS text LANGUAGE sql STABLE AS $$
    SELECT to_char(p_cas AT TIME ZONE 'UTC',
                   CASE WHEN (p_cas AT TIME ZONE 'UTC')::date = (now() AT TIME ZONE 'UTC')::date
                        THEN 'HH24:MI' ELSE 'FMDD. FMMM. HH24:MI' END)
$$;
COMMENT ON FUNCTION lkkl.cas_hlasky(timestamptz) IS 'Čas v UTC do chybové hlášky (jiný den i s datem).';

-- Popis druhého letu do hlášky: „vzlet 10:42 UTC, PIC Jan Novák“ nebo „10:42–11:05 UTC, PIC …“;
-- PIC se vynechá, je-li to osoba, o které hláška mluví.
CREATE FUNCTION lkkl.let_popis_hlasky(p_let_id bigint, p_krome_osoby bigint DEFAULT NULL)
RETURNS text LANGUAGE sql STABLE AS $$
    SELECT CASE WHEN l.cas_pristani IS NULL
                THEN 'vzlet ' || lkkl.cas_hlasky(l.cas_vzletu)
                ELSE lkkl.cas_hlasky(l.cas_vzletu) || '–' || to_char(l.cas_pristani AT TIME ZONE 'UTC', 'HH24:MI')
           END || ' UTC'
           || coalesce(', PIC ' || (SELECT o.jmeno || ' ' || o.prijmeni
                                    FROM lkkl.posadka p
                                    JOIN lkkl.lov_funkce f ON f.id = p.funkce_id AND f.kod = 'PIC'
                                    JOIN lkkl.lov_osoba o ON o.id = p.osoba_id
                                    WHERE p.let_id = l.id
                                      AND p.osoba_id IS DISTINCT FROM p_krome_osoby), '')
    FROM lkkl.let l
    WHERE l.id = p_let_id
$$;

-- Letadlo: kontrola před zápisem (dřív než omezení letadlo_bez_prekryvu, které neřekne, s čím
-- se let překrývá).
CREATE FUNCTION lkkl.let_letadlo_volne() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    r record;
BEGIN
    IF NEW.cas_vzletu IS NULL OR NEW.zruseni_duvod_id IS NOT NULL THEN
        RETURN NEW;
    END IF;
    SELECT l.id, a.rejstrik, l.cas_pristani
    INTO r
    FROM lkkl.let l
    JOIN lkkl.lov_letadlo a ON a.id = l.letadlo_id
    WHERE l.letadlo_id = NEW.letadlo_id AND l.id <> NEW.id
      AND l.cas_vzletu IS NOT NULL AND l.zruseni_duvod_id IS NULL
      AND tstzrange(l.cas_vzletu, l.cas_pristani) && tstzrange(NEW.cas_vzletu, NEW.cas_pristani)
    ORDER BY l.cas_vzletu
    LIMIT 1;
    IF FOUND THEN
        IF r.cas_pristani IS NULL THEN
            RAISE EXCEPTION '% už letí (%).', r.rejstrik, lkkl.let_popis_hlasky(r.id);
        END IF;
        RAISE EXCEPTION '% má v tu dobu jiný let (%).', r.rejstrik, lkkl.let_popis_hlasky(r.id);
    END IF;
    RETURN NEW;
END $$;
COMMENT ON FUNCTION lkkl.let_letadlo_volne() IS
    'Letadlo nesmí mít dva překrývající se lety – hláška s údaji druhého letu.';
CREATE TRIGGER let_letadlo_volne BEFORE INSERT OR UPDATE OF letadlo_id, cas_vzletu, cas_pristani, zruseni_duvod_id
    ON lkkl.let FOR EACH ROW EXECUTE FUNCTION lkkl.let_letadlo_volne();

-- Osoba: stejná kontrola jako v 018, hláška navíc s časem a PIC druhého letu.
CREATE OR REPLACE FUNCTION lkkl.let_osoby_bez_prekryvu(p_let_id bigint) RETURNS void LANGUAGE plpgsql AS $$
DECLARE
    r record;
BEGIN
    SELECT o.id AS osoba_id, o.jmeno || ' ' || o.prijmeni AS osoba, a.rejstrik, l2.id AS let2_id,
           l2.cas_pristani
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
        IF r.cas_pristani IS NULL THEN
            RAISE EXCEPTION 'Let %: % už letí na % (%).', p_let_id, r.osoba, r.rejstrik,
                lkkl.let_popis_hlasky(r.let2_id, r.osoba_id);
        END IF;
        RAISE EXCEPTION 'Let %: % je v tu dobu na palubě % (%).', p_let_id, r.osoba, r.rejstrik,
            lkkl.let_popis_hlasky(r.let2_id, r.osoba_id);
    END IF;
END $$;
