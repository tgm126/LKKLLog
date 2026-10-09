-- 041: Typy přezkoušení (návrh docs/modul-prezkouseni.md, rozhodnuto 9. 10. 2026).
-- Let s účelem Přezkoušení má místo úlohy typ přezkoušení (lov_prezkouseni, evidenční
-- číselník: kod = označení, zobrazuje se). Typ patří k jedné kategorii letadla a určuje, kdo
-- ho smí provést (lov_prezkouseni_opravneni) – podle toho se nabízí examinátor; role EXAMINATOR
-- (účel + funkce) se ruší. Úlohy se u přezkoušení nezadávají (II/9P „Přezkoušení CLOUD“ →
-- typ PC-CLOUD; jediný let na serveru se převede).
-- Počáteční typy a nová oprávnění FIE(A) a FE(S) – ověření FI(S) zakládá jednorázově tato
-- migrace (aby přišly na server); dál je zadává a mění uživatel v databázi. V nové databázi
-- vznikají kategorie a oprávnění až daty – tam totéž naplní 041_prezkouseni_data.sql.
-- Přejmenování (názvy, kódy beze změny): Výcvik sólo → Sólo pod dozorem, Žák → Pilot ve výcviku.

-- --- kód smí mít pomlčku: označení evidenčních číselníků (PC-SEP, ST-LAPL-A) --------------------
ALTER DOMAIN lkkl.kod DROP CONSTRAINT kod_check;
ALTER DOMAIN lkkl.kod ADD CONSTRAINT kod_check CHECK (VALUE ~ '^[A-Z0-9_-]+$');
COMMENT ON DOMAIN lkkl.kod IS
    'Kód položky číselníku: velká písmena, číslice, podtržítko, pomlčka. U řídicích číselníků jen pro program, u evidenčních oficiální označení (zobrazuje se).';

-- --- typy přezkoušení --------------------------------------------------------------------------
CREATE TABLE lkkl.lov_prezkouseni (
    id           bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    kod          lkkl.kod    NOT NULL UNIQUE,
    nazev        lkkl.nazev  NOT NULL,
    poradi       lkkl.poradi NOT NULL,
    platny       lkkl.platny NOT NULL,
    kategorie_id bigint      NOT NULL REFERENCES lkkl.lov_kategorie
);
COMMENT ON TABLE lkkl.lov_prezkouseni IS
    'Typ přezkoušení (zkouška dovednosti, přezkoušení odborné způsobilosti, ověření instruktora) – u letu s účelem Přezkoušení místo úlohy.';
COMMENT ON COLUMN lkkl.lov_prezkouseni.kod IS 'Označení typu (ST-SPL, PC-SEP…) – zobrazuje se (štítek pásku).';
COMMENT ON COLUMN lkkl.lov_prezkouseni.kategorie_id IS 'Kategorie letadla, na které se přezkoušení létá.';
CREATE INDEX lov_prezkouseni_kategorie ON lkkl.lov_prezkouseni (kategorie_id);

CREATE TABLE lkkl.lov_prezkouseni_opravneni (
    prezkouseni_id bigint NOT NULL REFERENCES lkkl.lov_prezkouseni,
    opravneni_id   bigint NOT NULL REFERENCES lkkl.lov_opravneni,
    PRIMARY KEY (prezkouseni_id, opravneni_id)
);
COMMENT ON TABLE lkkl.lov_prezkouseni_opravneni IS
    'Kdo smí přezkoušení provést (examinátor = PIC): oprávnění; nabídka examinátora v průvodci.';
CREATE INDEX lov_prezkouseni_opravneni_opravneni ON lkkl.lov_prezkouseni_opravneni (opravneni_id);

CREATE VIEW lkkl.v_lov_prezkouseni AS
SELECT id, kod, nazev, poradi, kategorie_id, kod || ' ' || nazev AS popis
FROM lkkl.lov_prezkouseni
WHERE platny
ORDER BY poradi, nazev;
COMMENT ON VIEW lkkl.v_lov_prezkouseni IS 'Nabídka: platné typy přezkoušení; popis = „PC-SEP Přezkoušení…“.';

-- Počáteční typy (zadání 9. 10. 2026; kategorie, která v databázi není, se přeskočí)
INSERT INTO lkkl.lov_prezkouseni (kod, nazev, poradi, platny, kategorie_id)
SELECT v.kod, v.nazev, v.poradi, true, k.id
FROM (VALUES
    ('ST-SPL',      'Zkouška dovednosti SPL',                                      10, 'KLUZAK'),
    ('PC-SPL',      'Přezkoušení odborné způsobilosti SPL',                        20, 'KLUZAK'),
    ('PC-CLOUD',    'Přezkoušení pro lety v oblacích',                             30, 'KLUZAK'),
    ('AOC-FI-S',    'Ověření způsobilosti instruktora FI(S)',                      40, 'KLUZAK'),
    ('ST-TMG',      'Zkouška dovednosti TMG',                                      50, 'TMG'),
    ('PC-TMG',      'Přezkoušení odborné způsobilosti TMG',                        60, 'TMG'),
    ('ST-LAPL-A',   'Zkouška dovednosti LAPL(A)',                                  70, 'LETOUN'),
    ('ST-PPL-A',    'Zkouška dovednosti PPL(A)',                                   80, 'LETOUN'),
    ('PC-LAPL-A',   'Přezkoušení odborné způsobilosti LAPL(A)',                    90, 'LETOUN'),
    ('PC-SEP',      'Přezkoušení odborné způsobilosti SEP (prodloužení, obnova)', 100, 'LETOUN'),
    ('AOC-FI-A',    'Ověření způsobilosti instruktora FI(A), CRI(A)',             110, 'LETOUN'),
    ('ST-ULL',      'Závěrečná zkouška pilota ULL',                               120, 'UL'),
    ('PC-ULL',      'Ověření praktických dovedností pilota ULL',                  130, 'UL'),
    ('ST-ULL-CTR',  'Zkouška pro řízené lety VFR',                                140, 'UL'),
    ('ST-ULL-VLEK', 'Zkouška kvalifikace vlekař ULL',                             150, 'UL'),
    ('AOC-ULLI',    'Přezkoušení instruktora ULL',                                160, 'UL')
) AS v(kod, nazev, poradi, kategorie)
JOIN lkkl.lov_kategorie k ON k.kod = v.kategorie;

-- Nová oprávnění: jen k typům přezkoušení (k rolím v letu neopravňují)
INSERT INTO lkkl.lov_opravneni (kod, nazev, poradi, platny) VALUES
    ('FIE_A',   'FIE(A) – examinátor instruktorů letounů', 52, true),
    ('FE_S_FI', 'FE(S) – ověření instruktorů FI(S)',       22, true);
INSERT INTO lkkl.lov_opravneni_kategorie (opravneni_id, kategorie_id)
SELECT o.id, k.id
FROM (VALUES ('FIE_A', 'LETOUN'), ('FIE_A', 'TMG'), ('FE_S_FI', 'KLUZAK'), ('FE_S_FI', 'TMG'))
     AS v(opravneni, kategorie)
JOIN lkkl.lov_opravneni o ON o.kod = v.opravneni
JOIN lkkl.lov_kategorie k ON k.kod = v.kategorie;

-- Kdo smí typ provést (oprávnění, které v databázi není, se přeskočí)
INSERT INTO lkkl.lov_prezkouseni_opravneni (prezkouseni_id, opravneni_id)
SELECT p.id, o.id
FROM (VALUES
    ('ST-SPL', 'FE_S'), ('PC-SPL', 'FE_S'), ('PC-CLOUD', 'FE_S'), ('AOC-FI-S', 'FE_S_FI'),
    ('ST-TMG', 'FE_S'), ('ST-TMG', 'FE_A'),
    ('PC-TMG', 'FE_S'), ('PC-TMG', 'FE_A'), ('PC-TMG', 'CRE_A'),
    ('ST-LAPL-A', 'FE_A'), ('ST-PPL-A', 'FE_A'), ('PC-LAPL-A', 'FE_A'),
    ('PC-SEP', 'FE_A'), ('PC-SEP', 'CRE_A'), ('AOC-FI-A', 'FIE_A'),
    ('ST-ULL', 'INSPEKTOR_ULL'), ('PC-ULL', 'INSPEKTOR_ULL'), ('ST-ULL-CTR', 'INSPEKTOR_ULL'),
    ('ST-ULL-VLEK', 'INSPEKTOR_ULL'), ('AOC-ULLI', 'INSPEKTOR_ULL')
) AS v(prezkouseni, opravneni)
JOIN lkkl.lov_prezkouseni p ON p.kod = v.prezkouseni
JOIN lkkl.lov_opravneni o ON o.kod = v.opravneni;

-- Kdo smí které přezkoušení provést: oprávnění osoby pro kategorii typu (jen platné položky)
CREATE VIEW lkkl.v_osoba_prezkouseni AS
SELECT DISTINCT oo.osoba_id, p.id AS prezkouseni_id
FROM lkkl.lov_osoba_opravneni oo
JOIN lkkl.lov_opravneni o ON o.id = oo.opravneni_id AND o.platny
JOIN lkkl.lov_prezkouseni_opravneni po ON po.opravneni_id = oo.opravneni_id
JOIN lkkl.lov_prezkouseni p ON p.id = po.prezkouseni_id AND p.platny
JOIN lkkl.lov_osoba_opravneni_kategorie ok
  ON ok.osoba_id = oo.osoba_id AND ok.opravneni_id = oo.opravneni_id
 AND ok.kategorie_id = p.kategorie_id
JOIN lkkl.lov_kategorie k ON k.id = p.kategorie_id AND k.platny;
COMMENT ON VIEW lkkl.v_osoba_prezkouseni IS
    'Která přezkoušení osoba smí provést (oprávnění pro kategorii typu) – nabídka examinátora.';

-- --- role EXAMINATOR se ruší: examinátor se nabízí podle typu přezkoušení -------------------
DELETE FROM lkkl.lov_opravneni_role orl USING lkkl.lov_role r
WHERE r.id = orl.role_id AND r.kod = 'EXAMINATOR';
DELETE FROM lkkl.lov_role WHERE kod = 'EXAMINATOR';

-- --- let: typ přezkoušení místo úlohy --------------------------------------------------------
ALTER TABLE lkkl.let ADD COLUMN prezkouseni_id bigint REFERENCES lkkl.lov_prezkouseni;
COMMENT ON COLUMN lkkl.let.prezkouseni_id IS
    'Typ přezkoušení – právě u účelu Přezkoušení (povinný, když pro kategorii letadla nějaký je); úloha se pak nezadává.';
CREATE INDEX let_prezkouseni ON lkkl.let (prezkouseni_id) WHERE prezkouseni_id IS NOT NULL;

-- --- přejmenování (jen názvy) ---------------------------------------------------------------
UPDATE lkkl.lov_ucel SET nazev = 'Sólo pod dozorem' WHERE kod = 'VYCVIK_SOLO';
UPDATE lkkl.lov_funkce SET nazev = 'Pilot ve výcviku' WHERE kod = 'ZAK';

-- --- platnost a audit ----------------------------------------------------------------------
CREATE TRIGGER platnost_prezkouseni BEFORE INSERT OR UPDATE OF prezkouseni_id ON lkkl.let
    FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('prezkouseni_id', 'lov_prezkouseni', 'Přezkoušení');
CREATE TRIGGER platnost_kategorie BEFORE INSERT OR UPDATE OF kategorie_id ON lkkl.lov_prezkouseni
    FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('kategorie_id', 'lov_kategorie', 'Kategorie');
CREATE TRIGGER platnost_prezkouseni BEFORE INSERT OR UPDATE OF prezkouseni_id ON lkkl.lov_prezkouseni_opravneni
    FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('prezkouseni_id', 'lov_prezkouseni', 'Přezkoušení');
CREATE TRIGGER platnost_opravneni BEFORE INSERT OR UPDATE OF opravneni_id ON lkkl.lov_prezkouseni_opravneni
    FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('opravneni_id', 'lov_opravneni', 'Oprávnění');

INSERT INTO lkkl.lov_audit_popisek (tabulka, sloupec, popisek, poradi, skryt_hodnotu)
VALUES ('let', 'prezkouseni_id', 'přezkoušení', 26, false);

-- --- kontrola letu (funkce celá; změna 041 v části Úloha) ------------------------------------
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

-- --- převod letů (až po nové kontrole letu) ---------------------------------------------------
-- Úlohy se u přezkoušení nenabízejí (vazby se ruší, povinnost se vypíná). Převod letů bez
-- historie – není to úprava uživatelem: přezkoušení s úlohou II/9P → PC-CLOUD; úloha se
-- u přezkoušení maže. Let přezkoušení, kterému typ nejde určit, kontrola odmítne.
UPDATE lkkl.lov_ucel SET uloha_povinna = false WHERE kod = 'PREZKOUSENI';
DELETE FROM lkkl.lov_uloha_ucel
WHERE ucel_id = (SELECT id FROM lkkl.lov_ucel WHERE kod = 'PREZKOUSENI');
ALTER TABLE lkkl.let DISABLE TRIGGER audit;
UPDATE lkkl.let l
SET prezkouseni_id = (SELECT p.id FROM lkkl.lov_prezkouseni p WHERE p.kod = 'PC-CLOUD'),
    uloha_id = NULL
FROM lkkl.lov_uloha u
JOIN lkkl.lov_osnova o ON o.id = u.osnova_id
WHERE u.id = l.uloha_id AND o.kod = 'II' AND u.kod = '9P'
  AND l.ucel_id = (SELECT id FROM lkkl.lov_ucel WHERE kod = 'PREZKOUSENI');
UPDATE lkkl.let SET uloha_id = NULL
WHERE uloha_id IS NOT NULL AND ucel_id = (SELECT id FROM lkkl.lov_ucel WHERE kod = 'PREZKOUSENI');
-- převedené lety projdou kontrolou hned (jinak by ALTER TABLE hlásil čekající kontroly)
SET CONSTRAINTS ALL IMMEDIATE;
ALTER TABLE lkkl.let ENABLE TRIGGER audit;

-- Úloha, která se nabízela jen u přezkoušení (II/9P), se smaže (bez letů), nebo zneplatní.
UPDATE lkkl.lov_uloha u SET platny = false
WHERE u.osnova_id = (SELECT id FROM lkkl.lov_osnova WHERE kod = 'II') AND u.kod = '9P'
  AND NOT EXISTS (SELECT 1 FROM lkkl.lov_uloha_ucel uu WHERE uu.uloha_id = u.id)
  AND EXISTS (SELECT 1 FROM lkkl.let l WHERE l.uloha_id = u.id);
DELETE FROM lkkl.lov_uloha u
WHERE u.osnova_id = (SELECT id FROM lkkl.lov_osnova WHERE kod = 'II') AND u.kod = '9P'
  AND NOT EXISTS (SELECT 1 FROM lkkl.lov_uloha_ucel uu WHERE uu.uloha_id = u.id)
  AND NOT EXISTS (SELECT 1 FROM lkkl.let l WHERE l.uloha_id = u.id);

-- --- v_let: typ přezkoušení (sloupce na konci) ----------------------------------------------
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
    pr.kod::text AS prezkouseni_kod
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

-- --- historie letu: typ přezkoušení čitelně („PC-SEP Přezkoušení…“) ------------------------
CREATE OR REPLACE FUNCTION lkkl.audit_hodnota(p_sloupec text, p_hodnota jsonb)
 RETURNS text
 LANGUAGE sql
 STABLE
AS $$
    SELECT CASE
        WHEN p_hodnota IS NULL OR p_hodnota = 'null'::jsonb THEN '—'
        WHEN p_sloupec = 'letadlo_id' THEN
            (SELECT rejstrik FROM lkkl.lov_letadlo WHERE id = (p_hodnota #>> '{}')::bigint)
        WHEN p_sloupec = 'vlecny_let_id' THEN
            (SELECT a.rejstrik FROM lkkl.let l JOIN lkkl.lov_letadlo a ON a.id = l.letadlo_id
             WHERE l.id = (p_hodnota #>> '{}')::bigint)
        WHEN p_sloupec IN ('osoba_id', 'platce_id', 'zalozil_id', 'zrusil_id') THEN
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
            to_char((p_hodnota #>> '{}')::timestamptz AT TIME ZONE 'UTC', 'HH24:MI:SS')
        WHEN p_sloupec IN ('pozvanka_odeslana', 'zablokovano_do') THEN
            to_char((p_hodnota #>> '{}')::timestamptz AT TIME ZONE 'UTC', 'FMDD. FMMM. YYYY HH24:MI')
        ELSE p_hodnota #>> '{}'
    END
$$;
