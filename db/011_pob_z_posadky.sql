-- 011: POB se u účelů s funkcemi (výcvik, sólo, přezkoušení) nezadává – odvodí se z posádky
-- (normální forma: neukládat, co jde odvodit). U ostatních letů je POB povinný.
-- v_let.pob ukazuje vždy skutečný počet osob na palubě.

ALTER TABLE lkkl.let ALTER COLUMN pob DROP NOT NULL;
COMMENT ON COLUMN lkkl.let.pob IS 'Počet osob na palubě celkem; zadává se jen u účelů bez funkcí (normální let, vlek). U výcviku, sóla a přezkoušení prázdné – odvodí se z posádky (v_let.pob).';

CREATE OR REPLACE FUNCTION lkkl.let_zkontrolovat(p_let_id bigint) RETURNS void LANGUAGE plpgsql AS $$
DECLARE
    l            lkkl.let;
    v_je_vlecny  boolean;
    v_na_palube  integer;
    v_picu       integer;
    v_mist       smallint;
    v_tg         integer;
    v_tg_mimo    boolean;
BEGIN
    SELECT * INTO l FROM lkkl.let WHERE id = p_let_id;
    IF NOT FOUND THEN
        RETURN;
    END IF;

    -- Vlek: účel chybí právě u vlečného letu; kluzák ve vleku vzlétá aerovlekem za vlečným letadlem.
    v_je_vlecny := EXISTS (SELECT 1 FROM lkkl.let k WHERE k.vlecny_let_id = l.id);
    IF (l.ucel_id IS NULL) <> v_je_vlecny THEN
        RAISE EXCEPTION 'Let %: účel chybí právě u vlečného letu (a jen u něj).', l.id;
    END IF;
    IF l.vlecny_let_id IS NOT NULL THEN
        IF (SELECT kod FROM lkkl.lov_zpusob_vzletu WHERE id = l.zpusob_vzletu_id) <> 'VLEK' THEN
            RAISE EXCEPTION 'Let %: vlečný let jde přiřadit jen při vzletu aerovlekem.', l.id;
        END IF;
        IF NOT (SELECT a.vlecne FROM lkkl.let v JOIN lkkl.letadlo a ON a.id = v.letadlo_id
                WHERE v.id = l.vlecny_let_id) THEN
            RAISE EXCEPTION 'Let %: vlekat smí jen letadlo s příznakem vlečné.', l.id;
        END IF;
    END IF;

    -- Posádka: právě jeden PIC; ostatní funkce přesně podle účelu.
    SELECT count(*) FILTER (WHERE f.kod = 'PIC'), count(*) FILTER (WHERE f.na_palube)
    INTO v_picu, v_na_palube
    FROM lkkl.posadka p JOIN lkkl.lov_funkce f ON f.id = p.funkce_id
    WHERE p.let_id = l.id;
    IF v_picu <> 1 THEN
        RAISE EXCEPTION 'Let %: musí mít právě jednoho PIC.', l.id;
    END IF;
    IF EXISTS (
        SELECT 1 FROM lkkl.posadka p JOIN lkkl.lov_funkce f ON f.id = p.funkce_id
        WHERE p.let_id = l.id AND f.kod <> 'PIC'
          AND NOT EXISTS (SELECT 1 FROM lkkl.ucel_funkce uf
                          WHERE uf.ucel_id = l.ucel_id AND uf.funkce_id = p.funkce_id)
    ) THEN
        RAISE EXCEPTION 'Let %: posádka má funkci, která k účelu letu nepatří.', l.id;
    END IF;
    IF EXISTS (
        SELECT 1 FROM lkkl.ucel_funkce uf
        WHERE uf.ucel_id = l.ucel_id
          AND NOT EXISTS (SELECT 1 FROM lkkl.posadka p WHERE p.let_id = l.id AND p.funkce_id = uf.funkce_id)
    ) THEN
        RAISE EXCEPTION 'Let %: v posádce chybí funkce, kterou účel letu vyžaduje.', l.id;
    END IF;

    -- POB: u účelů s funkcemi (výcvik, sólo, přezkoušení) se nezadává – odvodí se z posádky.
    -- Jinak je povinný: aspoň jmenovitě uvedené osoby na palubě. Vždy nejvýš počet míst typu.
    IF EXISTS (SELECT 1 FROM lkkl.ucel_funkce WHERE ucel_id = l.ucel_id) THEN
        IF l.pob IS NOT NULL THEN
            RAISE EXCEPTION 'Let %: u tohoto účelu se POB nezadává – odvodí se z posádky.', l.id;
        END IF;
    ELSIF l.pob IS NULL THEN
        RAISE EXCEPTION 'Let %: chybí POB.', l.id;
    ELSIF l.pob < v_na_palube THEN
        RAISE EXCEPTION 'Let %: POB je menší než počet jmenovitě uvedených osob na palubě.', l.id;
    END IF;
    SELECT t.pocet_mist INTO v_mist
    FROM lkkl.letadlo a JOIN lkkl.lov_typ t ON t.id = a.typ_id WHERE a.id = l.letadlo_id;
    IF coalesce(l.pob, v_na_palube) > v_mist THEN
        RAISE EXCEPTION 'Let %: na palubě je víc osob, než má letadlo míst (%).', l.id, v_mist;
    END IF;

    -- T&G: jen během letu a nejvýš tolik, kolik přistání bylo „navíc“.
    SELECT count(*), coalesce(bool_or(cas < l.cas_vzletu OR cas > l.cas_pristani), false)
    INTO v_tg, v_tg_mimo
    FROM lkkl.let_tg WHERE let_id = l.id;
    IF v_tg > 0 AND (l.cas_vzletu IS NULL OR v_tg_mimo) THEN
        RAISE EXCEPTION 'Let %: čas T&G je mimo dobu letu.', l.id;
    END IF;
    IF v_tg > l.pocet_pristani - 1 THEN
        RAISE EXCEPTION 'Let %: časů T&G je víc, než odpovídá počtu přistání.', l.id;
    END IF;
END $$;

CREATE OR REPLACE VIEW lkkl.v_let AS
SELECT l.id,
       CASE WHEN l.zruseni_duvod_id IS NOT NULL THEN 'ZRUSEN'
            WHEN l.cas_vzletu IS NULL THEN 'PRIPRAVEN'
            WHEN l.cas_pristani IS NULL THEN 'VE_VZDUCHU'
            ELSE 'UKONCEN' END                              AS stav,
       (coalesce(l.cas_vzletu, l.zalozeno) AT TIME ZONE 'UTC')::date AS den,
       l.letadlo_id, a.rejstrik, t.nazev AS typ, k.nazev AS kategorie, k.kod AS kategorie_kod,
       a.soukrome,
       l.ucel_id, u.nazev AS ucel, u.kod AS ucel_kod,
       v.id IS NOT NULL                                    AS je_vlecny,
       v.id                                                AS vleceny_let_id,
       l.vlecny_let_id,
       z.nazev AS zpusob_vzletu, z.kod AS zpusob_vzletu_kod,
       coalesce(lv.kod, l.misto_vzletu_popis)              AS misto_vzletu,
       coalesce(lp.kod, l.misto_pristani_popis)            AS misto_pristani,
       l.cas_vzletu, l.cas_pristani, l.doba_min,
       CASE WHEN l.zruseni_duvod_id IS NOT NULL OR l.doba_nulova THEN 0
            ELSE l.doba_min END                            AS doba_uctovana_min,
       l.pocet_pristani,
       coalesce(l.pob, (SELECT count(*) FROM lkkl.posadka p JOIN lkkl.lov_funkce f ON f.id = p.funkce_id
                        WHERE p.let_id = l.id AND f.na_palube))::smallint AS pob,
       pic.osoba_id AS pic_id, po.jmeno AS pic_jmeno, po.prijmeni AS pic_prijmeni,
       l.platce_id, l.plati_aeroklub, pl.jmeno AS platce_jmeno, pl.prijmeni AS platce_prijmeni,
       l.poznamka,
       l.zruseni_duvod_id, dz.nazev AS duvod_zruseni, l.zruseno,
       l.cas_pristani IS NOT NULL AND l.zalozeno > l.cas_pristani AS dodatecne,
       l.zalozil_id, l.zalozeno, l.verze
FROM lkkl.let l
JOIN lkkl.letadlo a                ON a.id = l.letadlo_id
JOIN lkkl.lov_typ t                ON t.id = a.typ_id
JOIN lkkl.lov_kategorie k          ON k.id = t.kategorie_id
JOIN lkkl.lov_zpusob_vzletu z      ON z.id = l.zpusob_vzletu_id
LEFT JOIN lkkl.lov_ucel u          ON u.id = l.ucel_id
LEFT JOIN lkkl.let v               ON v.vlecny_let_id = l.id
LEFT JOIN lkkl.lov_letiste lv      ON lv.id = l.misto_vzletu_id
LEFT JOIN lkkl.lov_letiste lp      ON lp.id = l.misto_pristani_id
LEFT JOIN lkkl.posadka pic         ON pic.let_id = l.id
                                  AND pic.funkce_id = (SELECT id FROM lkkl.lov_funkce WHERE kod = 'PIC')
LEFT JOIN lkkl.osoba po            ON po.id = pic.osoba_id
LEFT JOIN lkkl.osoba pl            ON pl.id = l.platce_id
LEFT JOIN lkkl.lov_duvod_zruseni dz ON dz.id = l.zruseni_duvod_id;
