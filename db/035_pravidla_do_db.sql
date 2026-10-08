-- 035: Pravidla a výpočty z aplikace do databáze (revize 8. 10. 2026, odsouhlaseno: body 1–5
-- a 7). Data na serveru je splňují (kontrolní dotazy 8. 10. 2026: všude 0).
-- 1. T&G jen u motorového letadla – ne u kluzáku ani vlečné (dosud jen server, bez vlečné).
-- 2. Vlek jako dvojice: kluzák a vlečná mají stejný čas vzletu, naplánovaný vlek se ruší
--    (i obnovuje) celý, vlekař není v posádce kluzáku (dosud jen server).
-- 3. Způsob vzletu podle kategorie: kluzák naviják nebo aerovlek, ostatní vlastní (dosud jen
--    frontend).
-- 4. Čas vzletu, přistání ani T&G nesmí být v budoucnosti (dosud jen server u nového letu).
-- 5. Druh provozu ve v_let: plachtařský (kluzák a vlečný let) / motorový (ostatní, i TMG) –
--    dosud počítal frontend pro souhrny; poslouží i uzávěrce a převodu do účetnictví.
-- 7. Poloha letadla ve v_lov_letadlo: místo posledního přistání vůbec (frontend ji bral jen
--    z dnešních letů – letadlo, které včera přistálo jinde, ukazoval doma).

-- --- 2. vlek jako dvojice ------------------------------------------------------------------
CREATE FUNCTION lkkl.vlek_zkontrolovat(p_kluzak bigint) RETURNS void
LANGUAGE plpgsql AS $$
DECLARE
    k lkkl.let;
    v lkkl.let;
BEGIN
    SELECT * INTO k FROM lkkl.let WHERE id = p_kluzak;
    IF NOT FOUND OR k.vlecny_let_id IS NULL THEN
        RETURN;
    END IF;
    SELECT * INTO v FROM lkkl.let WHERE id = k.vlecny_let_id;
    IF k.cas_vzletu IS DISTINCT FROM v.cas_vzletu THEN
        RAISE EXCEPTION 'Let %: kluzák a vlečná vzlétají společně – čas vzletu musí být stejný.', k.id;
    END IF;
    IF k.cas_vzletu IS NULL AND (k.zruseni_duvod_id IS NULL) <> (v.zruseni_duvod_id IS NULL) THEN
        RAISE EXCEPTION 'Let %: naplánovaný vlek se ruší i obnovuje celý.', k.id;
    END IF;
    IF EXISTS (SELECT 1 FROM lkkl.posadka pk JOIN lkkl.posadka pv ON pv.osoba_id = pk.osoba_id
               WHERE pk.let_id = k.id AND pv.let_id = v.id) THEN
        RAISE EXCEPTION 'Let %: vlekař nemůže být zároveň v posádce kluzáku.', k.id;
    END IF;
END $$;

COMMENT ON FUNCTION lkkl.vlek_zkontrolovat(bigint) IS
    'Kontrola dvojice vleku (z let_zkontrolovat): stejný vzlet, zrušení před vzletem celé, vlekař mimo posádku kluzáku.';

-- --- 1.–3. kontrola letu (funkce celá; změny označené 035) -------------------------------------
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

    -- T&G: jen během letu a nejvýš tolik, kolik přistání bylo „navíc“.
    SELECT count(*), coalesce(bool_or(cas < l.cas_vzletu OR cas > l.cas_pristani), false)
    INTO v_tg, v_tg_mimo
    FROM lkkl.let_tg WHERE let_id = l.id;
    IF v_tg > 0 AND (v_kat_kod = 'KLUZAK' OR v_je_vlecny) THEN
        RAISE EXCEPTION 'Let %: T&G jde jen u motorového letadla, ne u kluzáku ani vlečné.', l.id;
    END IF;
    IF v_tg > 0 AND (l.cas_vzletu IS NULL OR v_tg_mimo) THEN
        RAISE EXCEPTION 'Let %: čas T&G je mimo dobu letu.', l.id;
    END IF;
    IF v_tg > l.pocet_pristani - 1 THEN
        RAISE EXCEPTION 'Let %: časů T&G je víc, než odpovídá počtu přistání.', l.id;
    END IF;
END $$;

-- --- 4. čas ne v budoucnosti ------------------------------------------------------------------
CREATE FUNCTION lkkl.cas_ne_v_budoucnosti() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_TABLE_NAME = 'let_tg' THEN
        IF NEW.cas > now() THEN
            RAISE EXCEPTION 'Čas nesmí být v budoucnosti.';
        END IF;
    ELSIF NEW.cas_vzletu > now() OR NEW.cas_pristani > now() THEN
        RAISE EXCEPTION 'Čas nesmí být v budoucnosti.';
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER let_cas_ne_v_budoucnosti BEFORE INSERT OR UPDATE OF cas_vzletu, cas_pristani ON lkkl.let
    FOR EACH ROW EXECUTE FUNCTION lkkl.cas_ne_v_budoucnosti();
CREATE TRIGGER let_tg_cas_ne_v_budoucnosti BEFORE INSERT OR UPDATE OF cas ON lkkl.let_tg
    FOR EACH ROW EXECUTE FUNCTION lkkl.cas_ne_v_budoucnosti();

-- --- 5. druh provozu (sloupec na konci pohledu) --------------------------------------------------
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
    ul.nazev AS uloha,
        CASE
            WHEN k.kod::text = 'KLUZAK'::text OR v.id IS NOT NULL THEN 'PLACHTARSKY'::text
            ELSE 'MOTOROVY'::text
        END AS druh_provozu
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
     LEFT JOIN lkkl.lov_uloha ul ON ul.id = l.uloha_id;

COMMENT ON VIEW lkkl.v_let IS
    'Lety s odvozeným stavem, dnem (UTC datum vzletu), vlekem, účtovanou dobou, příznakem '
    '„dodatečně“ a druhem provozu (PLACHTARSKY = kluzák a vlečný let, MOTOROVY = ostatní).';

-- --- 7. poloha letadla (sloupec na konci pohledu) ------------------------------------------------
CREATE OR REPLACE VIEW lkkl.v_lov_letadlo AS
SELECT l.id, l.rejstrik, t.nazev AS typ, k.nazev AS kategorie, k.kod AS kategorie_kod,
       t.pocet_mist, l.max_doba_min, l.vlecne, l.soukrome, l.mimo_provoz,
       (SELECT coalesce(lp.kod::text, x.misto_pristani_popis)
        FROM lkkl.let x LEFT JOIN lkkl.lov_letiste lp ON lp.id = x.misto_pristani_id
        WHERE x.letadlo_id = l.id AND x.cas_pristani IS NOT NULL AND x.zruseni_duvod_id IS NULL
        ORDER BY x.cas_pristani DESC LIMIT 1) AS poloha
FROM lkkl.lov_letadlo l
JOIN lkkl.lov_typ t ON t.id = l.typ_id
JOIN lkkl.lov_kategorie k ON k.id = t.kategorie_id
WHERE l.platny
ORDER BY k.poradi, t.poradi, t.nazev, l.rejstrik;

COMMENT ON VIEW lkkl.v_lov_letadlo IS
    'Platná letadla pro nabídky a obrazovky: typ, kategorie, počet míst, poloha (místo '
    'posledního přistání); i mimo provoz (zobrazí se, nejdou vybrat). Vyřazená se neukazují.';
