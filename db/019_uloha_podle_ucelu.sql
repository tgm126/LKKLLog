-- 019: nabídka úlohy podle účelu na úrovni úlohy (ne celé osnovy) a povinnost úlohy jen tam,
-- kde pro účel a kategorii letadla nějaká úloha existuje.
--
-- Osnovy výcviku (Program výcviku na kluzácích AeČR v.6, úprava AK Kladno): v jedné osnově se
-- cvičení létají jen ve dvojím (výcvik), jen samostatně (sólo) nebo obojí; přezkoušení je jen
-- jedno cvičení osnovy. Proto vazba úloha ↔ účel (lov_uloha_ucel) místo osnova ↔ účel.

CREATE TABLE lkkl.lov_uloha_ucel (
    uloha_id bigint NOT NULL REFERENCES lkkl.lov_uloha,
    ucel_id  bigint NOT NULL REFERENCES lkkl.lov_ucel,
    PRIMARY KEY (uloha_id, ucel_id)
);
COMMENT ON TABLE lkkl.lov_uloha_ucel IS 'U kterých účelů letu se úloha nabízí (výcvik, sólo, normální, přezkoušení).';
CREATE INDEX lov_uloha_ucel_ucel ON lkkl.lov_uloha_ucel (ucel_id);

-- Dosavadní vazby osnov se přenesou na všechny jejich úlohy.
INSERT INTO lkkl.lov_uloha_ucel (uloha_id, ucel_id)
SELECT u.id, ou.ucel_id
FROM lkkl.lov_uloha u JOIN lkkl.lov_osnova_ucel ou ON ou.osnova_id = u.osnova_id;

DROP VIEW lkkl.v_uloha_nabidka;
CREATE VIEW lkkl.v_uloha_nabidka AS
SELECT u.id, u.nazev, u.poradi,
       o.id AS osnova_id, o.nazev AS osnova, o.poradi AS osnova_poradi,
       uu.ucel_id, o.kategorie_id
FROM lkkl.lov_uloha u
JOIN lkkl.lov_osnova o      ON o.id = u.osnova_id
JOIN lkkl.lov_uloha_ucel uu ON uu.uloha_id = u.id
WHERE u.platny AND o.platny
ORDER BY o.poradi, o.nazev, u.poradi, u.nazev;
COMMENT ON VIEW lkkl.v_uloha_nabidka IS 'Úlohy pro průvodce: filtrovat podle ucel_id a kategorie_id (prázdná = všechny kategorie).';

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
    IF v_tg > 0 AND (l.cas_vzletu IS NULL OR v_tg_mimo) THEN
        RAISE EXCEPTION 'Let %: čas T&G je mimo dobu letu.', l.id;
    END IF;
    IF v_tg > l.pocet_pristani - 1 THEN
        RAISE EXCEPTION 'Let %: časů T&G je víc, než odpovídá počtu přistání.', l.id;
    END IF;
END $$;

DROP TABLE lkkl.lov_osnova_ucel;
