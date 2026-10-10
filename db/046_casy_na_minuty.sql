-- 046: Časy letu – měření na sekundy, vše ostatní na minuty (docs/modul-lety.md 3.6,
-- rozhodnuto 10. 10. 2026). Naměřené časy se přejmenují na vzlet_namereno a pristani_namereno;
-- cas_vzletu a cas_pristani jsou nově generované minutové hodnoty: vzlet zaokrouhlený na
-- nejbližší minutu, přistání = vzlet + doba (doba se počítá ze sekund jako dřív). Doba tak
-- vždy přesně odpovídá rozdílu časů. Data se nepřevádějí – mění se jen odvozené hodnoty.
--
-- Přejmenování sloupce si s sebou vezmou omezení, indexy, generovaná doba a seznamy sloupců
-- triggerů (ukazují na sloupec, ne na jméno) – ty dál hlídají naměřené časy. Pohledy také
-- ukazují na sloupec, proto se založí znovu nad minutovými časy. Funkce (text) se čtou podle
-- jména: kontroly fyzické skutečnosti se přepíšou na naměřené časy; kde funkce čte z tabulky
-- cas_vzletu/cas_pristani (popis do hlášky, den letu, vlek), dostane minuty – tak je to správně.

-- --- zaokrouhlení na minuty a doba (definované jednou) ---------------------------------------
-- Neměnné (IMMUTABLE), aby šly do generovaných sloupců: aritmetika přes epochu v UTC
-- (timestamptz + interval ani date_bin nad timestamptz neměnné nejsou).
CREATE FUNCTION lkkl.na_minuty(p_cas timestamptz) RETURNS timestamptz
    LANGUAGE sql IMMUTABLE PARALLEL SAFE
    RETURN to_timestamp(946684800
        + floor((extract(epoch FROM p_cas - timestamptz '2000-01-01 00:00:00+00') + 30) / 60) * 60);
COMMENT ON FUNCTION lkkl.na_minuty(timestamptz) IS
    'Čas zaokrouhlený na nejbližší celou minutu (od 30 s nahoru).';

CREATE FUNCTION lkkl.doba_letu_min(p_vzlet timestamptz, p_pristani timestamptz) RETURNS integer
    LANGUAGE sql IMMUTABLE PARALLEL SAFE
    RETURN CASE WHEN p_pristani IS NOT NULL THEN
        greatest(1, floor((extract(epoch FROM p_pristani - p_vzlet) + 30) / 60))::integer
    END;
COMMENT ON FUNCTION lkkl.doba_letu_min(timestamptz, timestamptz) IS
    'Doba letu v celých minutách z naměřených časů: čistý čas zaokrouhlený (30 s a víc nahoru), '
    'nejméně 1 minuta; bez přistání prázdná.';

CREATE FUNCTION lkkl.pristani_na_minuty(p_vzlet timestamptz, p_pristani timestamptz) RETURNS timestamptz
    LANGUAGE sql IMMUTABLE PARALLEL SAFE
    RETURN to_timestamp(946684800
        + extract(epoch FROM lkkl.na_minuty(p_vzlet) - timestamptz '2000-01-01 00:00:00+00')
        + 60 * lkkl.doba_letu_min(p_vzlet, p_pristani));
COMMENT ON FUNCTION lkkl.pristani_na_minuty(timestamptz, timestamptz) IS
    'Přistání na minuty = vzlet na minuty + doba; bez přistání prázdné.';

-- --- tabulka let -------------------------------------------------------------------------------
ALTER TABLE lkkl.let RENAME COLUMN cas_vzletu TO vzlet_namereno;
ALTER TABLE lkkl.let RENAME COLUMN cas_pristani TO pristani_namereno;
COMMENT ON COLUMN lkkl.let.vzlet_namereno IS
    'Naměřený vzlet (UTC, na sekundy – určuje server); ručně zadaný na celé minuty. Jinde než '
    'v kontrolách a stopkách se nepoužívá – čte se cas_vzletu.';
COMMENT ON COLUMN lkkl.let.pristani_namereno IS
    'Naměřené přistání (UTC, na sekundy – určuje server); ručně zadané na celé minuty. Jinde než '
    'v kontrolách se nepoužívá – čte se cas_pristani.';

ALTER TABLE lkkl.let ALTER COLUMN doba_min SET EXPRESSION AS
    (lkkl.doba_letu_min(vzlet_namereno, pristani_namereno));  -- stejný výpočet jako dřív
ALTER TABLE lkkl.let ADD COLUMN cas_vzletu timestamptz
    GENERATED ALWAYS AS (lkkl.na_minuty(vzlet_namereno)) STORED;
ALTER TABLE lkkl.let ADD COLUMN cas_pristani timestamptz
    GENERATED ALWAYS AS (lkkl.pristani_na_minuty(vzlet_namereno, pristani_namereno)) STORED;
COMMENT ON COLUMN lkkl.let.cas_vzletu IS 'Vzlet na minuty (UTC): naměřený zaokrouhlený na nejbližší minutu.';
COMMENT ON COLUMN lkkl.let.cas_pristani IS 'Přistání na minuty (UTC) = cas_vzletu + doba_min.';
COMMENT ON COLUMN lkkl.let.doba_min IS
    'Doba letu v celých minutách: čistý naměřený čas zaokrouhlený (30 s a víc nahoru), nejméně '
    '1 minuta; = cas_pristani − cas_vzletu.';

-- index pro dotazy podle dne (den letu se počítá z minutového vzletu)
DROP INDEX lkkl.let_cas_vzletu;
CREATE INDEX let_cas_vzletu ON lkkl.let (cas_vzletu);

-- --- kontroly nad naměřenými časy ------------------------------------------------------------
CREATE OR REPLACE FUNCTION lkkl.cas_ne_v_budoucnosti() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_TABLE_NAME = 'let_tg' THEN
        IF NEW.cas > now() THEN
            RAISE EXCEPTION 'Čas nesmí být v budoucnosti.';
        END IF;
    ELSIF NEW.vzlet_namereno > now() OR NEW.pristani_namereno > now() THEN
        RAISE EXCEPTION 'Čas nesmí být v budoucnosti.';
    END IF;
    RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION lkkl.let_letadlo_volne() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    r record;
BEGIN
    IF NEW.vzlet_namereno IS NULL OR NEW.zruseni_duvod_id IS NOT NULL THEN
        RETURN NEW;
    END IF;
    SELECT l.id, a.rejstrik, l.pristani_namereno
    INTO r
    FROM lkkl.let l
    JOIN lkkl.lov_letadlo a ON a.id = l.letadlo_id
    WHERE l.letadlo_id = NEW.letadlo_id AND l.id <> NEW.id
      AND l.vzlet_namereno IS NOT NULL AND l.zruseni_duvod_id IS NULL
      AND tstzrange(l.vzlet_namereno, l.pristani_namereno)
          && tstzrange(NEW.vzlet_namereno, NEW.pristani_namereno)
    ORDER BY l.vzlet_namereno
    LIMIT 1;
    IF FOUND THEN
        IF r.pristani_namereno IS NULL THEN
            RAISE EXCEPTION '% už letí (%).', r.rejstrik, lkkl.let_popis_hlasky(r.id);
        END IF;
        RAISE EXCEPTION '% má v tu dobu jiný let (%).', r.rejstrik, lkkl.let_popis_hlasky(r.id);
    END IF;
    RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION lkkl.let_osoby_bez_prekryvu(p_let_id bigint) RETURNS void LANGUAGE plpgsql AS $$
DECLARE
    r record;
BEGIN
    SELECT o.id AS osoba_id, o.jmeno || ' ' || o.prijmeni AS osoba, a.rejstrik, l2.id AS let2_id,
           l2.pristani_namereno
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
      AND l.vzlet_namereno IS NOT NULL AND l.zruseni_duvod_id IS NULL
      AND l2.vzlet_namereno IS NOT NULL AND l2.zruseni_duvod_id IS NULL
      -- bez přistání = ve vzduchu (rozsah bez horní meze); přistání a vzlet ve stejnou chvíli jde
      AND tstzrange(l.vzlet_namereno, l.pristani_namereno)
          && tstzrange(l2.vzlet_namereno, l2.pristani_namereno)
    LIMIT 1;
    IF FOUND THEN
        IF r.pristani_namereno IS NULL THEN
            RAISE EXCEPTION 'Let %: % už letí na % (%).', p_let_id, r.osoba, r.rejstrik,
                lkkl.let_popis_hlasky(r.let2_id, r.osoba_id);
        END IF;
        RAISE EXCEPTION 'Let %: % je v tu dobu na palubě % (%).', p_let_id, r.osoba, r.rejstrik,
            lkkl.let_popis_hlasky(r.let2_id, r.osoba_id);
    END IF;
END $$;

-- --- kontrola letu (funkce celá; změna 046: T&G uvnitř naměřeného letu) ---------------------
CREATE OR REPLACE FUNCTION lkkl.let_zkontrolovat(p_let_id bigint)
 RETURNS void
 LANGUAGE plpgsql
AS $$
DECLARE
    l            lkkl.let;
    v_je_vlecny  boolean;
    v_na_palube  integer;
    v_picu       integer;
    v_mist       smallint;
    v_tg         integer;
    v_tg_mimo    boolean;
    v_kategorie  bigint;
    v_kat_kod    text;
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
        IF NOT (SELECT a.vlecne FROM lkkl.let v JOIN lkkl.lov_letadlo a ON a.id = v.letadlo_id
                WHERE v.id = l.vlecny_let_id) THEN
            RAISE EXCEPTION 'Let %: vlekat smí jen letadlo s příznakem vlečné.', l.id;
        END IF;
    -- Aerovlek vždy s letem vlečné (032): i cizí vlečná je v lov_letadlo (soukromé, vlečné).
    ELSIF (SELECT kod FROM lkkl.lov_zpusob_vzletu WHERE id = l.zpusob_vzletu_id) = 'VLEK' THEN
        RAISE EXCEPTION 'Let %: při vzletu aerovlekem chybí let vlečné.', l.id;
    END IF;
    -- Vlek jako dvojice (035) – z kluzáku i z vlečné
    IF l.vlecny_let_id IS NOT NULL THEN
        PERFORM lkkl.vlek_zkontrolovat(l.id);
    END IF;
    IF v_je_vlecny THEN
        PERFORM lkkl.vlek_zkontrolovat((SELECT k.id FROM lkkl.let k WHERE k.vlecny_let_id = l.id));
    END IF;

    -- Způsob vzletu podle kategorie (035): kluzák naviják nebo aerovlek, ostatní vlastní.
    SELECT k.kod INTO v_kat_kod
    FROM lkkl.lov_letadlo a JOIN lkkl.lov_typ t ON t.id = a.typ_id
    JOIN lkkl.lov_kategorie k ON k.id = t.kategorie_id WHERE a.id = l.letadlo_id;
    IF (v_kat_kod = 'KLUZAK')
       <> ((SELECT kod FROM lkkl.lov_zpusob_vzletu WHERE id = l.zpusob_vzletu_id) IN ('NAVIJAK', 'VLEK')) THEN
        RAISE EXCEPTION 'Let %: kluzák vzlétá navijákem nebo aerovlekem, ostatní letadla vlastním pohonem.', l.id;
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
          AND NOT EXISTS (SELECT 1 FROM lkkl.lov_ucel_funkce uf
                          WHERE uf.ucel_id = l.ucel_id AND uf.funkce_id = p.funkce_id)
    ) THEN
        RAISE EXCEPTION 'Let %: posádka má funkci, která k účelu letu nepatří.', l.id;
    END IF;
    IF EXISTS (
        SELECT 1 FROM lkkl.lov_ucel_funkce uf
        WHERE uf.ucel_id = l.ucel_id
          AND NOT EXISTS (SELECT 1 FROM lkkl.posadka p WHERE p.let_id = l.id AND p.funkce_id = uf.funkce_id)
    ) THEN
        RAISE EXCEPTION 'Let %: v posádce chybí funkce, kterou účel letu vyžaduje.', l.id;
    END IF;

    -- POB: u účelů s funkcemi (výcvik, sólo, přezkoušení) se nezadává – odvodí se z posádky.
    -- Jinak je povinný: aspoň jmenovitě uvedené osoby na palubě. Vždy nejvýš počet míst typu.
    IF EXISTS (SELECT 1 FROM lkkl.lov_ucel_funkce WHERE ucel_id = l.ucel_id) THEN
        IF l.pob IS NOT NULL THEN
            RAISE EXCEPTION 'Let %: u tohoto účelu se POB nezadává – odvodí se z posádky.', l.id;
        END IF;
    ELSIF l.pob IS NULL THEN
        RAISE EXCEPTION 'Let %: chybí POB.', l.id;
    ELSIF l.pob < v_na_palube THEN
        RAISE EXCEPTION 'Let %: POB je menší než počet jmenovitě uvedených osob na palubě.', l.id;
    END IF;
    SELECT t.pocet_mist INTO v_mist
    FROM lkkl.lov_letadlo a JOIN lkkl.lov_typ t ON t.id = a.typ_id WHERE a.id = l.letadlo_id;
    IF coalesce(l.pob, v_na_palube) > v_mist THEN
        RAISE EXCEPTION 'Let %: na palubě je víc osob, než má letadlo míst (%).', l.id, v_mist;
    END IF;

    -- Úloha: jen z nabídky pro účel letu (lov_uloha_ucel) a kategorii letadla (osnova pro
    -- kategorii, nebo pro všechny). Povinná podle účelu (lov_ucel.uloha_povinna) – ale jen když
    -- pro účel a kategorii letadla nějaká platná úloha existuje (jinak by let nešel zapsat).
    SELECT t.kategorie_id INTO v_kategorie
    FROM lkkl.lov_letadlo a JOIN lkkl.lov_typ t ON t.id = a.typ_id WHERE a.id = l.letadlo_id;
    IF l.uloha_id IS NULL THEN
        IF (SELECT uloha_povinna FROM lkkl.lov_ucel WHERE id = l.ucel_id) AND EXISTS (
            SELECT 1 FROM lkkl.v_uloha_nabidka n
            WHERE n.ucel_id = l.ucel_id
              AND (n.kategorie_id IS NULL OR n.kategorie_id = v_kategorie)
        ) THEN
            RAISE EXCEPTION 'Let %: u tohoto účelu je úloha povinná.', l.id;
        END IF;
    ELSIF NOT EXISTS (
        SELECT 1
        FROM lkkl.lov_uloha u
        JOIN lkkl.lov_osnova o ON o.id = u.osnova_id
        JOIN lkkl.lov_uloha_ucel uu ON uu.uloha_id = u.id AND uu.ucel_id = l.ucel_id
        WHERE u.id = l.uloha_id AND (o.kategorie_id IS NULL OR o.kategorie_id = v_kategorie)
    ) THEN
        RAISE EXCEPTION 'Let %: úloha nepatří k účelu letu nebo ke kategorii letadla.', l.id;
    END IF;

    -- Typ přezkoušení (041): jen u účelu Přezkoušení a na kategorii letadla; povinný, když pro
    -- kategorii nějaký platný typ existuje.
    IF coalesce((SELECT kod = 'PREZKOUSENI' FROM lkkl.lov_ucel WHERE id = l.ucel_id), false) THEN
        IF l.prezkouseni_id IS NULL THEN
            IF EXISTS (SELECT 1 FROM lkkl.v_lov_prezkouseni WHERE kategorie_id = v_kategorie) THEN
                RAISE EXCEPTION 'Let %: u přezkoušení je typ přezkoušení povinný.', l.id;
            END IF;
        ELSIF (SELECT kategorie_id FROM lkkl.lov_prezkouseni WHERE id = l.prezkouseni_id) <> v_kategorie THEN
            RAISE EXCEPTION 'Let %: typ přezkoušení patří k jiné kategorii letadla.', l.id;
        END IF;
    ELSIF l.prezkouseni_id IS NOT NULL THEN
        RAISE EXCEPTION 'Let %: typ přezkoušení jde jen u účelu Přezkoušení.', l.id;
    END IF;

    -- T&G: jen během letu a nejvýš tolik, kolik přistání bylo „navíc“.
    SELECT count(*), coalesce(bool_or(cas < l.vzlet_namereno OR cas > l.pristani_namereno), false)
    INTO v_tg, v_tg_mimo
    FROM lkkl.let_tg WHERE let_id = l.id;
    IF v_tg > 0 AND (v_kat_kod = 'KLUZAK' OR v_je_vlecny) THEN
        RAISE EXCEPTION 'Let %: T&G jde jen u motorového letadla, ne u kluzáku ani vlečné.', l.id;
    END IF;
    IF v_tg > 0 AND (l.vzlet_namereno IS NULL OR v_tg_mimo) THEN
        RAISE EXCEPTION 'Let %: čas T&G je mimo dobu letu.', l.id;
    END IF;
    IF v_tg > l.pocet_pristani - 1 THEN
        RAISE EXCEPTION 'Let %: časů T&G je víc, než odpovídá počtu přistání.', l.id;
    END IF;
END $$;

-- --- historie: časy na minuty (T&G je měření – zaokrouhlí se) --------------------------------
CREATE OR REPLACE FUNCTION lkkl.audit_hodnota(p_sloupec text, p_hodnota jsonb)
 RETURNS text
 LANGUAGE sql
 STABLE
AS $$
    SELECT coalesce(CASE
        WHEN p_hodnota IS NULL OR p_hodnota = 'null'::jsonb THEN '—'
        WHEN p_sloupec = 'letadlo_id' THEN
            (SELECT rejstrik FROM lkkl.lov_letadlo WHERE id = (p_hodnota #>> '{}')::bigint)
        WHEN p_sloupec = 'vlecny_let_id' THEN
            (SELECT a.rejstrik FROM lkkl.let l JOIN lkkl.lov_letadlo a ON a.id = l.letadlo_id
             WHERE l.id = (p_hodnota #>> '{}')::bigint)
        WHEN p_sloupec IN ('osoba_id', 'platce_id', 'zalozil_id', 'zrusil_id', 'odeslal_id') THEN
            (SELECT jmeno || ' ' || prijmeni FROM lkkl.lov_osoba WHERE id = (p_hodnota #>> '{}')::bigint)
        WHEN p_sloupec = 'ucel_id' THEN
            (SELECT nazev FROM lkkl.lov_ucel WHERE id = (p_hodnota #>> '{}')::bigint)
        WHEN p_sloupec = 'zpusob_vzletu_id' THEN
            (SELECT nazev FROM lkkl.lov_zpusob_vzletu WHERE id = (p_hodnota #>> '{}')::bigint)
        WHEN p_sloupec = 'funkce_id' THEN
            (SELECT nazev FROM lkkl.lov_funkce WHERE id = (p_hodnota #>> '{}')::bigint)
        WHEN p_sloupec = 'zruseni_duvod_id' THEN
            (SELECT nazev FROM lkkl.lov_duvod_zruseni WHERE id = (p_hodnota #>> '{}')::bigint)
        WHEN p_sloupec = 'uloha_id' THEN
            (SELECT o.kod || '/' || u.kod || ' ' || u.nazev FROM lkkl.lov_uloha u
             JOIN lkkl.lov_osnova o ON o.id = u.osnova_id WHERE u.id = (p_hodnota #>> '{}')::bigint)
        WHEN p_sloupec = 'prezkouseni_id' THEN
            (SELECT kod || ' ' || nazev FROM lkkl.lov_prezkouseni WHERE id = (p_hodnota #>> '{}')::bigint)
        WHEN p_sloupec = 'opravneni_id' THEN
            (SELECT nazev FROM lkkl.lov_opravneni WHERE id = (p_hodnota #>> '{}')::bigint)
        WHEN p_sloupec = 'kategorie_id' THEN
            (SELECT nazev FROM lkkl.lov_kategorie WHERE id = (p_hodnota #>> '{}')::bigint)
        WHEN p_sloupec = 'typ_id' THEN
            (SELECT nazev FROM lkkl.lov_typ WHERE id = (p_hodnota #>> '{}')::bigint)
        WHEN p_sloupec IN ('misto_vzletu_id', 'misto_pristani_id') THEN
            (SELECT kod FROM lkkl.lov_letiste WHERE id = (p_hodnota #>> '{}')::bigint)
        WHEN jsonb_typeof(p_hodnota) = 'boolean' THEN
            CASE WHEN p_hodnota::boolean THEN 'ano' ELSE 'ne' END
        WHEN p_sloupec IN ('cas_vzletu', 'cas_pristani', 'cas') THEN
            to_char(lkkl.na_minuty((p_hodnota #>> '{}')::timestamptz) AT TIME ZONE 'UTC', 'HH24:MI')
        WHEN p_sloupec IN ('pozvanka_odeslana', 'zablokovano_do') THEN
            to_char((p_hodnota #>> '{}')::timestamptz AT TIME ZONE 'UTC', 'FMDD. FMMM. YYYY HH24:MI')
        ELSE p_hodnota #>> '{}'
    END, '#' || (p_hodnota #>> '{}'))  -- cíl vazby už neexistuje: aspoň jeho id
$$;

-- --- pohledy znovu nad minutovými časy (beze změny textu; v_let navíc vzlet_namereno) --------
CREATE OR REPLACE VIEW lkkl.v_let AS
 SELECT l.id,
        CASE
            WHEN l.zruseni_duvod_id IS NOT NULL THEN 'ZRUSEN'::text
            WHEN l.cas_vzletu IS NULL THEN 'NAPLANOVAN'::text
            WHEN l.cas_pristani IS NULL THEN 'VE_VZDUCHU'::text
            ELSE 'UKONCEN'::text
        END AS stav,
    (COALESCE(l.cas_vzletu, l.zalozeno) AT TIME ZONE 'UTC'::text)::date AS den,
    l.letadlo_id,
    a.rejstrik,
    t.nazev AS typ,
    k.nazev AS kategorie,
    k.kod AS kategorie_kod,
    a.soukrome,
    l.ucel_id,
    u.nazev AS ucel,
    u.kod AS ucel_kod,
    v.id IS NOT NULL AS je_vlecny,
    v.id AS vleceny_let_id,
    l.vlecny_let_id,
    z.nazev AS zpusob_vzletu,
    z.kod AS zpusob_vzletu_kod,
    COALESCE(lv.kod::text, l.misto_vzletu_popis) AS misto_vzletu,
    COALESCE(lp.kod::text, l.misto_pristani_popis) AS misto_pristani,
    l.cas_vzletu,
    l.cas_pristani,
    l.doba_min,
        CASE
            WHEN l.zruseni_duvod_id IS NOT NULL THEN 0
            ELSE l.doba_min
        END AS doba_uctovana_min,
    l.pocet_pristani,
    COALESCE(l.pob::bigint, ( SELECT count(*) AS count
           FROM lkkl.posadka p
             JOIN lkkl.lov_funkce f ON f.id = p.funkce_id
          WHERE p.let_id = l.id AND f.na_palube))::smallint AS pob,
    pic.osoba_id AS pic_id,
    po.jmeno AS pic_jmeno,
    po.prijmeni AS pic_prijmeni,
    l.platce_id,
    l.plati_aeroklub,
    pl.jmeno AS platce_jmeno,
    pl.prijmeni AS platce_prijmeni,
    l.poznamka,
    l.zruseni_duvod_id,
    dz.nazev AS duvod_zruseni,
    l.zruseno,
    l.cas_pristani IS NOT NULL AND l.zalozeno > l.cas_pristani AS dodatecne,
    l.zalozil_id,
    l.zalozeno,
    l.verze,
    l.uloha_id,
    (ulo.kod::text || '/' || ul.kod::text || ' ' || ul.nazev::text)::lkkl.nazev AS uloha,
        CASE
            WHEN k.kod::text = 'KLUZAK'::text OR v.id IS NOT NULL THEN 'PLACHTARSKY'::text
            ELSE 'MOTOROVY'::text
        END AS druh_provozu,
    l.cas_vzletu IS NOT NULL AND l.cas_pristani IS NULL AND l.zruseni_duvod_id IS NULL AND a.max_doba_min IS NOT NULL AND (now() - l.cas_vzletu) > (a.max_doba_min::double precision * '00:01:00'::interval) AS prekrocena_doba,
    ulo.kod::text || '/' || ul.kod::text AS uloha_oznaceni,
    l.prezkouseni_id,
    pr.kod::text || ' ' || pr.nazev::text AS prezkouseni,
    pr.kod::text AS prezkouseni_kod,
    l.vzlet_namereno
   FROM lkkl.let l
     JOIN lkkl.lov_letadlo a ON a.id = l.letadlo_id
     JOIN lkkl.lov_typ t ON t.id = a.typ_id
     JOIN lkkl.lov_kategorie k ON k.id = t.kategorie_id
     JOIN lkkl.lov_zpusob_vzletu z ON z.id = l.zpusob_vzletu_id
     LEFT JOIN lkkl.lov_ucel u ON u.id = l.ucel_id
     LEFT JOIN lkkl.let v ON v.vlecny_let_id = l.id
     LEFT JOIN lkkl.lov_letiste lv ON lv.id = l.misto_vzletu_id
     LEFT JOIN lkkl.lov_letiste lp ON lp.id = l.misto_pristani_id
     LEFT JOIN lkkl.posadka pic ON pic.let_id = l.id AND pic.funkce_id = (( SELECT lov_funkce.id
           FROM lkkl.lov_funkce
          WHERE lov_funkce.kod::text = 'PIC'::text))
     LEFT JOIN lkkl.lov_osoba po ON po.id = pic.osoba_id
     LEFT JOIN lkkl.lov_osoba pl ON pl.id = l.platce_id
     LEFT JOIN lkkl.lov_duvod_zruseni dz ON dz.id = l.zruseni_duvod_id
     LEFT JOIN lkkl.lov_uloha ul ON ul.id = l.uloha_id
     LEFT JOIN lkkl.lov_osnova ulo ON ulo.id = ul.osnova_id
     LEFT JOIN lkkl.lov_prezkouseni pr ON pr.id = l.prezkouseni_id;
COMMENT ON COLUMN lkkl.v_let.vzlet_namereno IS 'Naměřený vzlet na sekundy – jen pro stopky letu ve vzduchu.';

CREATE OR REPLACE VIEW lkkl.v_lov_letadlo AS
SELECT l.id, l.rejstrik, t.nazev AS typ, k.nazev AS kategorie, k.kod AS kategorie_kod,
       t.pocet_mist, l.max_doba_min, l.vlecne, l.soukrome, l.mimo_provoz,
       coalesce(p.kod::text, p.misto_pristani_popis) AS poloha,
       p.misto_pristani_id AS poloha_letiste_id,
       p.misto_pristani_popis AS poloha_popis
FROM lkkl.lov_letadlo l
JOIN lkkl.lov_typ t ON t.id = l.typ_id
JOIN lkkl.lov_kategorie k ON k.id = t.kategorie_id
LEFT JOIN LATERAL (
    SELECT x.misto_pristani_id, x.misto_pristani_popis, lp.kod
    FROM lkkl.let x LEFT JOIN lkkl.lov_letiste lp ON lp.id = x.misto_pristani_id
    WHERE x.letadlo_id = l.id AND x.cas_pristani IS NOT NULL AND x.zruseni_duvod_id IS NULL
    ORDER BY x.cas_pristani DESC LIMIT 1
) p ON true
WHERE l.platny
ORDER BY k.poradi, t.poradi, t.nazev, l.rejstrik;
