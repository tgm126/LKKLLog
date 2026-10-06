-- 009: lety, posádka, časy T&G, pravidla a pohled v_let.
--
-- Zásady (docs/tabulky.md): stav letu se neukládá, odvodí se; POB je jediný údaj o počtu lidí
-- na palubě, jménem jsou jen funkce z lov_funkce (normální let: jen PIC); vlek se odvodí
-- z vazby kluzák → vlečný let; „soukromé“ z letadla; let se nemaže, jen zruší.
-- Místo vzletu a přistání se při zadání nevyžaduje: nezadané doplní trigger domovským letištěm
-- (úprava kdykoli v detailu). Letadlo smí mít zároveň let ve vzduchu i připravené lety.
-- Úloha z osnovy přibude s číselníky osnov a úloh.

CREATE EXTENSION IF NOT EXISTS btree_gist;  -- pro EXCLUDE (letadlo + časový rozsah)

-- Které funkce (kromě PIC) účel vyžaduje; právě tyto a žádné jiné. Pravidla programu → struktura.
CREATE TABLE lkkl.ucel_funkce (
    ucel_id   bigint NOT NULL REFERENCES lkkl.lov_ucel,
    funkce_id bigint NOT NULL REFERENCES lkkl.lov_funkce,
    PRIMARY KEY (ucel_id, funkce_id)
);
COMMENT ON TABLE lkkl.ucel_funkce IS 'Povinné funkce účelu kromě PIC (výcvik → žák, sólo → dozor, přezkoušení → přezkoušený).';
INSERT INTO lkkl.ucel_funkce (ucel_id, funkce_id)
SELECT u.id, f.id
FROM (VALUES ('VYCVIK', 'ZAK'), ('VYCVIK_SOLO', 'DOZOR'), ('PREZKOUSENI', 'PREZKOUSENY')) AS v(ucel, funkce)
JOIN lkkl.lov_ucel u ON u.kod = v.ucel
JOIN lkkl.lov_funkce f ON f.kod = v.funkce;

CREATE TABLE lkkl.let (
    id                   bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    letadlo_id           bigint      NOT NULL REFERENCES lkkl.letadlo,
    ucel_id              bigint      REFERENCES lkkl.lov_ucel,
    zpusob_vzletu_id     bigint      NOT NULL REFERENCES lkkl.lov_zpusob_vzletu,
    vlecny_let_id        bigint      UNIQUE REFERENCES lkkl.let,

    misto_vzletu_id      bigint      REFERENCES lkkl.lov_letiste,
    misto_vzletu_popis   text        CHECK (btrim(misto_vzletu_popis) <> ''),
    misto_pristani_id    bigint      REFERENCES lkkl.lov_letiste,
    misto_pristani_popis text        CHECK (btrim(misto_pristani_popis) <> ''),
    cas_vzletu           timestamptz,
    cas_pristani         timestamptz,
    doba_min             integer     GENERATED ALWAYS AS (
                             floor((extract(epoch FROM cas_pristani - cas_vzletu) + 30) / 60)::integer
                         ) STORED,
    doba_nulova          boolean     NOT NULL DEFAULT false,
    pocet_pristani       smallint,
    pob                  smallint    NOT NULL CHECK (pob BETWEEN 1 AND 20),

    platce_id            bigint      REFERENCES lkkl.osoba,
    plati_aeroklub       boolean     NOT NULL DEFAULT false,
    poznamka             text        CHECK (btrim(poznamka) <> ''),

    zruseni_duvod_id     bigint      REFERENCES lkkl.lov_duvod_zruseni,
    zruseno              timestamptz,
    zrusil_id            bigint      REFERENCES lkkl.osoba,

    zalozil_id           bigint      NOT NULL REFERENCES lkkl.osoba,
    zalozeno             timestamptz NOT NULL DEFAULT now(),
    verze                integer     NOT NULL DEFAULT 1,

    CONSTRAINT neni_vlastni_vlek     CHECK (vlecny_let_id <> id),
    CONSTRAINT misto_vzletu_jedno    CHECK ((misto_vzletu_id IS NULL) <> (misto_vzletu_popis IS NULL)),
    CONSTRAINT misto_pristani_nejvys_jedno CHECK (misto_pristani_id IS NULL OR misto_pristani_popis IS NULL),
    CONSTRAINT pristani_po_vzletu    CHECK (cas_pristani IS NULL OR (cas_vzletu IS NOT NULL AND cas_pristani >= cas_vzletu)),
    CONSTRAINT pristani_ma_misto_a_pocet CHECK (
        (cas_pristani IS NULL AND misto_pristani_id IS NULL AND misto_pristani_popis IS NULL AND pocet_pristani IS NULL)
        OR (cas_pristani IS NOT NULL AND (misto_pristani_id IS NOT NULL OR misto_pristani_popis IS NOT NULL)
            AND pocet_pristani >= 1)),
    CONSTRAINT doba_nulova_jen_kratky CHECK (NOT doba_nulova OR (cas_pristani IS NOT NULL AND cas_pristani - cas_vzletu <= interval '1 minute')),
    CONSTRAINT prave_jeden_platce    CHECK (plati_aeroklub = (platce_id IS NULL)),
    CONSTRAINT zruseni_uplne         CHECK ((zruseni_duvod_id IS NULL) = (zruseno IS NULL) AND (zrusil_id IS NULL OR zruseno IS NOT NULL)),
    -- Jedno letadlo nemůže mít dva časově překrývající se lety; let ve vzduchu trvá „do nekonečna“.
    CONSTRAINT letadlo_bez_prekryvu EXCLUDE USING gist (letadlo_id WITH =, tstzrange(cas_vzletu, cas_pristani) WITH &&)
        WHERE (cas_vzletu IS NOT NULL AND zruseni_duvod_id IS NULL)
);
COMMENT ON TABLE lkkl.let IS 'Let. Stav se odvodí (v_let): bez vzletu = připravený, vzlet bez přistání = ve vzduchu, obojí = ukončený, důvod zrušení = zrušený.';
COMMENT ON COLUMN lkkl.let.ucel_id IS 'Prázdné právě u vlečného letu (vlek se odvodí z vazby).';
COMMENT ON COLUMN lkkl.let.vlecny_let_id IS 'U kluzáku vzlétajícího aerovlekem: let vlečného letadla.';
COMMENT ON COLUMN lkkl.let.misto_vzletu_id IS 'Nezadané doplní trigger domovským letištěm.';
COMMENT ON COLUMN lkkl.let.misto_vzletu_popis IS 'Místo mimo letiště (terén); jinak misto_vzletu_id.';
COMMENT ON COLUMN lkkl.let.misto_pristani_id IS 'Při přistání nezadané doplní trigger domovským letištěm.';
COMMENT ON COLUMN lkkl.let.misto_pristani_popis IS 'Přistání do terénu (popis místa); jinak misto_pristani_id.';
COMMENT ON COLUMN lkkl.let.cas_vzletu IS 'UTC, na sekundy; čas určuje server.';
COMMENT ON COLUMN lkkl.let.doba_min IS 'Doba letu v celých minutách (30 s a víc nahoru) – počítá databáze.';
COMMENT ON COLUMN lkkl.let.doba_nulova IS 'Let do 1 minuty (přetržené lano): start se počítá, doba se účtuje 0.';
COMMENT ON COLUMN lkkl.let.pocet_pristani IS 'Počet přistání včetně posledního (T&G = počet − 1); vyplní se při přistání.';
COMMENT ON COLUMN lkkl.let.pob IS 'Počet osob na palubě celkem (včetně jmenovitě uvedených).';
COMMENT ON COLUMN lkkl.let.verze IS 'Číslo verze záznamu – chrání opravu před přepsáním souběžnou změnou; zvyšuje trigger.';

CREATE INDEX let_cas_vzletu ON lkkl.let (cas_vzletu);
CREATE INDEX let_letadlo ON lkkl.let (letadlo_id);

CREATE TABLE lkkl.posadka (
    let_id    bigint NOT NULL REFERENCES lkkl.let,
    osoba_id  bigint NOT NULL REFERENCES lkkl.osoba,
    funkce_id bigint NOT NULL REFERENCES lkkl.lov_funkce,
    PRIMARY KEY (let_id, osoba_id),
    UNIQUE (let_id, funkce_id)
);
COMMENT ON TABLE lkkl.posadka IS 'Jmenovitě uvedené osoby letu; každá funkce nejvýš jednou, osoba nejvýš jednou.';
CREATE INDEX posadka_osoba ON lkkl.posadka (osoba_id);

CREATE TABLE lkkl.let_tg (
    let_id bigint      NOT NULL REFERENCES lkkl.let,
    cas    timestamptz NOT NULL,
    PRIMARY KEY (let_id, cas)
);
COMMENT ON TABLE lkkl.let_tg IS 'Časy jednotlivých touch-and-go (nepovinné; dopsané lety je nemají).';

-- --- pravidla přes více řádků a tabulek: jedna kontrola, spouští se na konci transakce ------

CREATE FUNCTION lkkl.let_zkontrolovat(p_let_id bigint) RETURNS void LANGUAGE plpgsql AS $$
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

    -- POB: aspoň jmenovitě uvedené osoby na palubě, nejvýš počet míst typu (je-li zadaný).
    IF l.pob < v_na_palube THEN
        RAISE EXCEPTION 'Let %: POB je menší než počet jmenovitě uvedených osob na palubě.', l.id;
    END IF;
    SELECT t.pocet_mist INTO v_mist
    FROM lkkl.letadlo a JOIN lkkl.lov_typ t ON t.id = a.typ_id WHERE a.id = l.letadlo_id;
    IF l.pob > v_mist THEN
        RAISE EXCEPTION 'Let %: POB je větší než počet míst letadla (%).', l.id, v_mist;
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

CREATE FUNCTION lkkl.let_kontrola() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_TABLE_NAME = 'let' THEN
        PERFORM lkkl.let_zkontrolovat(NEW.id);
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
        END IF;
    END IF;
    RETURN NULL;
END $$;

CREATE CONSTRAINT TRIGGER let_kontrola AFTER INSERT OR UPDATE ON lkkl.let
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION lkkl.let_kontrola();
CREATE CONSTRAINT TRIGGER posadka_kontrola AFTER INSERT OR UPDATE OR DELETE ON lkkl.posadka
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION lkkl.let_kontrola();
CREATE CONSTRAINT TRIGGER let_tg_kontrola AFTER INSERT OR UPDATE OR DELETE ON lkkl.let_tg
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION lkkl.let_kontrola();

-- Nezadané místo vzletu (a při přistání místo přistání) = domovské letiště.
CREATE FUNCTION lkkl.let_doplnit_misto() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    v_domovske bigint := (SELECT id FROM lkkl.lov_letiste WHERE domovske);
BEGIN
    IF NEW.misto_vzletu_id IS NULL AND NEW.misto_vzletu_popis IS NULL THEN
        NEW.misto_vzletu_id := v_domovske;
    END IF;
    IF NEW.cas_pristani IS NOT NULL AND NEW.misto_pristani_id IS NULL AND NEW.misto_pristani_popis IS NULL THEN
        NEW.misto_pristani_id := v_domovske;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER let_doplnit_misto BEFORE INSERT OR UPDATE ON lkkl.let
    FOR EACH ROW EXECUTE FUNCTION lkkl.let_doplnit_misto();

-- Verze záznamu se zvyšuje při každé změně; let se nemaže.
CREATE FUNCTION lkkl.let_verze() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    NEW.verze := OLD.verze + 1;
    RETURN NEW;
END $$;
CREATE TRIGGER let_verze BEFORE UPDATE ON lkkl.let FOR EACH ROW EXECUTE FUNCTION lkkl.let_verze();

CREATE FUNCTION lkkl.let_nemazat() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Let se nemaže, jen se zruší s důvodem.';
END $$;
CREATE TRIGGER let_nemazat BEFORE DELETE ON lkkl.let FOR EACH ROW EXECUTE FUNCTION lkkl.let_nemazat();

-- --- pohled pro obrazovky a výpisy -------------------------------------------------------------

CREATE VIEW lkkl.v_let AS
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
       l.pocet_pristani, l.pob,
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
COMMENT ON VIEW lkkl.v_let IS 'Lety s odvozeným stavem, dnem (UTC datum vzletu), vlekem, účtovanou dobou a příznakem „dodatečně“.';
