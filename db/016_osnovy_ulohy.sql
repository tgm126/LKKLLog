-- 016: osnovy a úlohy (číselníky podle standardu), úloha u letu.
--
-- Úlohy jsou členěné do osnov (např. kluzáky: základní, pokračovací, sportovní výcvik; obecné
-- úlohy jako samostatná osnova). Osnova patří ke kategorii letadla (prázdná = ke všem).
-- osnova_ucel říká, u kterých účelů se osnova nabízí; lov_ucel.uloha_povinna, u kterých je
-- úloha povinná. Označení úlohy (např. „B3“) je součástí názvu, kod je jen pro program.

CREATE TABLE lkkl.lov_osnova (
    id           bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    kod          lkkl.kod    NOT NULL UNIQUE,
    nazev        lkkl.nazev  NOT NULL,
    poradi       lkkl.poradi NOT NULL,
    platny       lkkl.platny NOT NULL,
    kategorie_id bigint      REFERENCES lkkl.lov_kategorie
);
COMMENT ON TABLE lkkl.lov_osnova IS 'Osnova (skupina úloh), např. Základní výcvik; obecné úlohy jako osnova Obecné.';
COMMENT ON COLUMN lkkl.lov_osnova.kategorie_id IS 'Kategorie letadla, pro kterou osnova platí; prázdné = pro všechny.';

CREATE TABLE lkkl.lov_uloha (
    id        bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    kod       lkkl.kod    NOT NULL UNIQUE,
    nazev     lkkl.nazev  NOT NULL,
    poradi    lkkl.poradi NOT NULL,
    platny    lkkl.platny NOT NULL,
    osnova_id bigint      NOT NULL REFERENCES lkkl.lov_osnova
);
COMMENT ON TABLE lkkl.lov_uloha IS 'Úloha osnovy; označení (např. B3) je součástí názvu.';
CREATE INDEX lov_uloha_osnova ON lkkl.lov_uloha (osnova_id);

CREATE TABLE lkkl.osnova_ucel (
    osnova_id bigint NOT NULL REFERENCES lkkl.lov_osnova,
    ucel_id   bigint NOT NULL REFERENCES lkkl.lov_ucel,
    PRIMARY KEY (osnova_id, ucel_id)
);
COMMENT ON TABLE lkkl.osnova_ucel IS 'U kterých účelů letu se osnova nabízí.';

ALTER TABLE lkkl.lov_ucel ADD COLUMN uloha_povinna boolean NOT NULL DEFAULT false;
COMMENT ON COLUMN lkkl.lov_ucel.uloha_povinna IS 'Let s tímto účelem musí mít úlohu.';
UPDATE lkkl.lov_ucel SET uloha_povinna = true WHERE kod IN ('VYCVIK', 'VYCVIK_SOLO', 'PREZKOUSENI');

ALTER TABLE lkkl.let ADD COLUMN uloha_id bigint REFERENCES lkkl.lov_uloha;
COMMENT ON COLUMN lkkl.let.uloha_id IS 'Úloha z osnovy; povinnost podle účelu, kontrola v let_zkontrolovat.';
CREATE INDEX let_uloha ON lkkl.let (uloha_id) WHERE uloha_id IS NOT NULL;

INSERT INTO lkkl.audit_popisek (tabulka, sloupec, popisek, poradi) VALUES ('let', 'uloha_id', 'úloha', 25);

-- Nabídky podle standardu
CREATE VIEW lkkl.v_lov_osnova AS
SELECT id, kod, nazev, poradi, kategorie_id
FROM lkkl.lov_osnova WHERE platny ORDER BY poradi, nazev;
COMMENT ON VIEW lkkl.v_lov_osnova IS 'Nabídka: platné osnovy.';

CREATE VIEW lkkl.v_lov_uloha AS
SELECT id, kod, nazev, poradi, osnova_id
FROM lkkl.lov_uloha WHERE platny ORDER BY poradi, nazev;
COMMENT ON VIEW lkkl.v_lov_uloha IS 'Nabídka: platné úlohy.';

-- Nabídka úloh pro průvodce: platná úloha z platné osnovy, pro účel a kategorii letadla.
CREATE VIEW lkkl.v_uloha_nabidka AS
SELECT u.id, u.nazev, u.poradi,
       o.id AS osnova_id, o.nazev AS osnova, o.poradi AS osnova_poradi,
       ou.ucel_id, o.kategorie_id
FROM lkkl.lov_uloha u
JOIN lkkl.lov_osnova o   ON o.id = u.osnova_id
JOIN lkkl.osnova_ucel ou ON ou.osnova_id = o.id
WHERE u.platny AND o.platny
ORDER BY o.poradi, o.nazev, u.poradi, u.nazev;
COMMENT ON VIEW lkkl.v_uloha_nabidka IS 'Úlohy pro průvodce: filtrovat podle ucel_id a kategorie_id (prázdná = všechny kategorie).';

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

    -- Úloha: povinná podle účelu (lov_ucel.uloha_povinna); smí být jen z osnovy, která se
    -- k účelu nabízí (osnova_ucel) a patří ke kategorii letadla (nebo ke všem kategoriím).
    IF l.uloha_id IS NULL THEN
        IF (SELECT uloha_povinna FROM lkkl.lov_ucel WHERE id = l.ucel_id) THEN
            RAISE EXCEPTION 'Let %: u tohoto účelu je úloha povinná.', l.id;
        END IF;
    ELSIF NOT EXISTS (
        SELECT 1
        FROM lkkl.lov_uloha u
        JOIN lkkl.lov_osnova o ON o.id = u.osnova_id
        JOIN lkkl.osnova_ucel ou ON ou.osnova_id = o.id AND ou.ucel_id = l.ucel_id
        JOIN lkkl.letadlo a ON a.id = l.letadlo_id
        JOIN lkkl.lov_typ t ON t.id = a.typ_id
        WHERE u.id = l.uloha_id AND (o.kategorie_id IS NULL OR o.kategorie_id = t.kategorie_id)
    ) THEN
        RAISE EXCEPTION 'Let %: úloha nepatří k účelu letu nebo ke kategorii letadla.', l.id;
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
            WHEN l.cas_vzletu IS NULL THEN 'NAPLANOVAN'
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
       l.zalozil_id, l.zalozeno, l.verze,
       l.uloha_id, ul.nazev AS uloha
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
LEFT JOIN lkkl.lov_duvod_zruseni dz ON dz.id = l.zruseni_duvod_id
LEFT JOIN lkkl.lov_uloha ul ON ul.id = l.uloha_id;

CREATE OR REPLACE FUNCTION lkkl.audit_hodnota(p_sloupec text, p_hodnota jsonb) RETURNS text
LANGUAGE sql STABLE AS $$
    SELECT CASE
        WHEN p_hodnota IS NULL OR p_hodnota = 'null'::jsonb THEN '—'
        WHEN p_sloupec = 'letadlo_id' THEN
            (SELECT rejstrik FROM lkkl.letadlo WHERE id = (p_hodnota #>> '{}')::bigint)
        WHEN p_sloupec = 'vlecny_let_id' THEN
            (SELECT a.rejstrik FROM lkkl.let l JOIN lkkl.letadlo a ON a.id = l.letadlo_id
             WHERE l.id = (p_hodnota #>> '{}')::bigint)
        WHEN p_sloupec IN ('osoba_id', 'platce_id', 'zalozil_id', 'zrusil_id') THEN
            (SELECT jmeno || ' ' || prijmeni FROM lkkl.osoba WHERE id = (p_hodnota #>> '{}')::bigint)
        WHEN p_sloupec = 'ucel_id' THEN
            (SELECT nazev FROM lkkl.lov_ucel WHERE id = (p_hodnota #>> '{}')::bigint)
        WHEN p_sloupec = 'zpusob_vzletu_id' THEN
            (SELECT nazev FROM lkkl.lov_zpusob_vzletu WHERE id = (p_hodnota #>> '{}')::bigint)
        WHEN p_sloupec = 'funkce_id' THEN
            (SELECT nazev FROM lkkl.lov_funkce WHERE id = (p_hodnota #>> '{}')::bigint)
        WHEN p_sloupec = 'zruseni_duvod_id' THEN
            (SELECT nazev FROM lkkl.lov_duvod_zruseni WHERE id = (p_hodnota #>> '{}')::bigint)
        WHEN p_sloupec = 'uloha_id' THEN
            (SELECT nazev FROM lkkl.lov_uloha WHERE id = (p_hodnota #>> '{}')::bigint)
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
