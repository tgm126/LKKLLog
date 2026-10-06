-- 012: auditní log – zapisuje ho databáze triggerem (zachytí i přímou úpravu v databázi).
--
-- Ukládá se přesně (technicky): klíč řádku a změněné sloupce „z → na“ v JSON. Čitelnou
-- podobu skládají pohledy v_audit a v_historie_letu – nic se neukládá dvakrát.
-- Sleduje se: let, posadka, let_tg, osoba, ucet (bez hesla a technických sloupců), letadlo.
-- Číselníky a relace ne. Audit jde jen doplňovat.
--
-- Kdo změnu udělal: aplikace na začátku požadavku nastaví proměnné relace databáze
--   lkkl.zdroj = 'aplikace', lkkl.osoba_id = <kdo jedná>, lkkl.puvodni_osoba_id = <skutečný
--   admin při „přihlásit se jako“>. Bez nich jde o přímou úpravu v databázi.

CREATE TABLE lkkl.audit (
    id               bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    kdy              timestamptz NOT NULL DEFAULT now(),
    transakce        bigint      NOT NULL DEFAULT (pg_current_xact_id()::text::bigint),
    tabulka          text        NOT NULL,
    klic             jsonb       NOT NULL,
    operace          text        NOT NULL CHECK (operace IN ('INSERT', 'UPDATE', 'DELETE')),
    zmeny            jsonb       NOT NULL,
    zdroj            text        NOT NULL CHECK (zdroj IN ('aplikace', 'databaze')),
    osoba_id         bigint      REFERENCES lkkl.osoba,
    puvodni_osoba_id bigint      REFERENCES lkkl.osoba,
    db_uzivatel      text        NOT NULL DEFAULT session_user,
    let_id           bigint      GENERATED ALWAYS AS (
                         CASE WHEN tabulka = 'let' THEN (klic ->> 'id')::bigint
                              WHEN tabulka IN ('posadka', 'let_tg') THEN (klic ->> 'let_id')::bigint
                         END) STORED
);
COMMENT ON TABLE lkkl.audit IS 'Auditní log: kdo, kdy a co změnil. Jen doplňovat. Čitelně: v_audit, v_historie_letu.';
COMMENT ON COLUMN lkkl.audit.transakce IS 'Číslo transakce – změny jedné akce (let + posádka) mají stejné.';
COMMENT ON COLUMN lkkl.audit.klic IS 'Primární klíč změněného řádku, např. {"id": 15} nebo {"let_id": 15, "osoba_id": 3}.';
COMMENT ON COLUMN lkkl.audit.zmeny IS 'INSERT: nový řádek, DELETE: starý řádek, UPDATE: jen změněné sloupce {"sloupec": {"z": …, "na": …}}.';
COMMENT ON COLUMN lkkl.audit.zdroj IS 'aplikace, nebo databaze (přímá úprava).';
COMMENT ON COLUMN lkkl.audit.let_id IS 'Let, ke kterému změna patří (let, posádka, T&G) – pro historii letu.';

CREATE INDEX audit_let ON lkkl.audit (let_id) WHERE let_id IS NOT NULL;
CREATE INDEX audit_tabulka_kdy ON lkkl.audit (tabulka, kdy);

-- --- zápis: jedna obecná funkce pro všechny sledované tabulky ---------------------------------
-- Argumenty triggeru = sloupce, které se do auditu nepíšou (šum, hesla).

CREATE FUNCTION lkkl.audit_zapsat() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    v_vynechat text[] := coalesce(TG_ARGV, '{}');
    v_stary    jsonb;
    v_novy     jsonb;
    v_zmeny    jsonb;
    v_klic     jsonb;
BEGIN
    IF TG_OP <> 'INSERT' THEN v_stary := to_jsonb(OLD) - v_vynechat; END IF;
    IF TG_OP <> 'DELETE' THEN v_novy := to_jsonb(NEW) - v_vynechat; END IF;

    IF TG_OP = 'UPDATE' THEN
        SELECT jsonb_object_agg(k, jsonb_build_object('z', v_stary -> k, 'na', v_novy -> k))
        INTO v_zmeny
        FROM jsonb_object_keys(v_novy) AS k
        WHERE v_stary -> k IS DISTINCT FROM v_novy -> k;
        IF v_zmeny IS NULL THEN
            RETURN NULL;  -- změnily se jen vynechané sloupce
        END IF;
    ELSE
        v_zmeny := coalesce(v_novy, v_stary);
    END IF;

    SELECT jsonb_object_agg(a.attname, coalesce(to_jsonb(NEW), to_jsonb(OLD)) -> a.attname)
    INTO v_klic
    FROM pg_index i
    JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY (i.indkey)
    WHERE i.indrelid = TG_RELID AND i.indisprimary;

    INSERT INTO lkkl.audit (tabulka, klic, operace, zmeny, zdroj, osoba_id, puvodni_osoba_id)
    VALUES (TG_TABLE_NAME, v_klic, TG_OP, v_zmeny,
            CASE WHEN current_setting('lkkl.zdroj', true) = 'aplikace' THEN 'aplikace' ELSE 'databaze' END,
            nullif(current_setting('lkkl.osoba_id', true), '')::bigint,
            nullif(current_setting('lkkl.puvodni_osoba_id', true), '')::bigint);
    RETURN NULL;
END $$;

CREATE TRIGGER audit AFTER INSERT OR UPDATE OR DELETE ON lkkl.let
    FOR EACH ROW EXECUTE FUNCTION lkkl.audit_zapsat('verze');
CREATE TRIGGER audit AFTER INSERT OR UPDATE OR DELETE ON lkkl.posadka
    FOR EACH ROW EXECUTE FUNCTION lkkl.audit_zapsat();
CREATE TRIGGER audit AFTER INSERT OR UPDATE OR DELETE ON lkkl.let_tg
    FOR EACH ROW EXECUTE FUNCTION lkkl.audit_zapsat();
CREATE TRIGGER audit AFTER INSERT OR UPDATE OR DELETE ON lkkl.osoba
    FOR EACH ROW EXECUTE FUNCTION lkkl.audit_zapsat();
CREATE TRIGGER audit AFTER INSERT OR UPDATE OR DELETE ON lkkl.ucet
    FOR EACH ROW EXECUTE FUNCTION lkkl.audit_zapsat('heslo_hash', 'posledni_prihlaseni', 'neuspesne_pokusy');
CREATE TRIGGER audit AFTER INSERT OR UPDATE OR DELETE ON lkkl.letadlo
    FOR EACH ROW EXECUTE FUNCTION lkkl.audit_zapsat();

-- Audit jde jen doplňovat.
CREATE FUNCTION lkkl.audit_jen_doplnovat() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Auditní log jde jen doplňovat.';
END $$;
CREATE TRIGGER audit_jen_doplnovat BEFORE UPDATE OR DELETE ON lkkl.audit
    FOR EACH ROW EXECUTE FUNCTION lkkl.audit_jen_doplnovat();
CREATE TRIGGER audit_bez_vyprazdneni BEFORE TRUNCATE ON lkkl.audit
    FOR EACH STATEMENT EXECUTE FUNCTION lkkl.audit_jen_doplnovat();

-- --- čitelná podoba -------------------------------------------------------------------------

-- Popisky sloupců pro historii. Co tu není, je technické a v čitelné historii se neukazuje.
CREATE TABLE lkkl.audit_popisek (
    tabulka       text     NOT NULL,
    sloupec       text     NOT NULL,
    popisek       text     NOT NULL,
    poradi        smallint NOT NULL,
    skryt_hodnotu boolean  NOT NULL DEFAULT false,
    PRIMARY KEY (tabulka, sloupec)
);
COMMENT ON TABLE lkkl.audit_popisek IS 'Popisky sloupců v čitelné historii a jejich pořadí. Sloupec bez popisku se neukazuje.';
COMMENT ON COLUMN lkkl.audit_popisek.skryt_hodnotu IS 'Ukáže se jen, že se změnilo (heslo, telefon); popisek je pak celá věta.';
INSERT INTO lkkl.audit_popisek (tabulka, sloupec, popisek, poradi, skryt_hodnotu) VALUES
    ('let', 'letadlo_id', 'letadlo', 10, false),
    ('let', 'ucel_id', 'účel', 20, false),
    ('let', 'zpusob_vzletu_id', 'způsob vzletu', 30, false),
    ('let', 'vlecny_let_id', 'vlek za', 40, false),
    ('let', 'misto_vzletu_id', 'místo vzletu', 50, false),
    ('let', 'misto_vzletu_popis', 'místo vzletu', 51, false),
    ('let', 'cas_vzletu', 'vzlet', 60, false),
    ('let', 'misto_pristani_id', 'místo přistání', 70, false),
    ('let', 'misto_pristani_popis', 'místo přistání', 71, false),
    ('let', 'cas_pristani', 'přistání', 80, false),
    ('let', 'pocet_pristani', 'přistání celkem', 90, false),
    ('let', 'doba_nulova', 'doba 0 (krátký let)', 95, false),
    ('let', 'pob', 'POB', 100, false),
    ('let', 'platce_id', 'platí', 110, false),
    ('let', 'plati_aeroklub', 'platí aeroklub', 111, false),
    ('let', 'poznamka', 'poznámka', 120, false),
    ('let', 'zruseni_duvod_id', 'důvod', 130, false),
    ('let_tg', 'cas', 'T&G', 10, false),
    ('osoba', 'jmeno', 'jméno', 10, false),
    ('osoba', 'prijmeni', 'příjmení', 20, false),
    ('osoba', 'email', 'e-mail', 30, false),
    ('osoba', 'telefon', 'změněn telefon', 40, true),
    ('osoba', 'cislo_clena', 'číslo člena', 50, false),
    ('osoba', 'clen', 'člen', 60, false),
    ('osoba', 'aktivni', 'aktivní', 70, false),
    ('ucet', 'aktivni', 'aktivní', 10, false),
    ('ucet', 'admin', 'admin', 20, false),
    ('ucet', 'smi_odblokovat', 'smí odblokovat', 30, false),
    ('ucet', 'heslo_zmeneno', 'změněno heslo', 40, true),
    ('ucet', 'pozvanka_odeslana', 'pozvánka', 50, false),
    ('ucet', 'zablokovano_do', 'zablokováno do', 60, false),
    ('letadlo', 'rejstrik', 'rejstřík', 10, false),
    ('letadlo', 'typ_id', 'typ', 20, false),
    ('letadlo', 'soukrome', 'soukromé', 30, false),
    ('letadlo', 'max_doba_min', 'max. doba letu [min]', 40, false),
    ('letadlo', 'vlecne', 'vlečné', 50, false);

-- Hodnota sloupce čitelně: identifikátory na jména, časy UTC, ano/ne.
CREATE FUNCTION lkkl.audit_hodnota(p_sloupec text, p_hodnota jsonb) RETURNS text
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

-- Název akce odvozený z toho, co se změnilo.
CREATE FUNCTION lkkl.audit_akce(p_tabulka text, p_operace text, z jsonb) RETURNS text
LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE p_tabulka
        WHEN 'let' THEN CASE
            WHEN p_operace = 'INSERT' THEN 'Založení letu'
            WHEN p_operace = 'DELETE' THEN 'Smazání letu'
            WHEN z ? 'zruseni_duvod_id' AND z -> 'zruseni_duvod_id' -> 'na' <> 'null' THEN 'Zrušení'
            WHEN z ? 'zruseni_duvod_id' THEN 'Obnovení letu'
            WHEN z ? 'cas_pristani' AND z -> 'cas_pristani' -> 'z' = 'null' THEN 'Přistání'
            WHEN z ? 'cas_pristani' AND z -> 'cas_pristani' -> 'na' = 'null' THEN 'Zpět: přistání'
            WHEN z ? 'cas_vzletu' AND z -> 'cas_vzletu' -> 'z' = 'null' THEN 'Vzlet'
            WHEN z ? 'cas_vzletu' AND z -> 'cas_vzletu' -> 'na' = 'null' THEN 'Zpět: vzlet'
            ELSE 'Úprava' END
        WHEN 'posadka' THEN CASE p_operace
            WHEN 'INSERT' THEN 'Posádka' WHEN 'DELETE' THEN 'Posádka: odebrání' ELSE 'Úprava posádky' END
        WHEN 'let_tg' THEN CASE p_operace
            WHEN 'INSERT' THEN 'T&G' WHEN 'DELETE' THEN 'Zpět: T&G' ELSE 'Úprava T&G' END
        WHEN 'osoba' THEN CASE p_operace
            WHEN 'INSERT' THEN 'Založení osoby' WHEN 'DELETE' THEN 'Smazání osoby' ELSE 'Úprava osoby' END
        WHEN 'ucet' THEN CASE
            WHEN p_operace = 'INSERT' THEN 'Aktivace účtu'
            WHEN p_operace = 'DELETE' THEN 'Zrušení účtu'
            WHEN z -> 'aktivni' -> 'na' = 'false' THEN 'Zablokování účtu'
            WHEN z -> 'aktivni' -> 'na' = 'true' THEN 'Odblokování účtu'
            WHEN z ? 'heslo_zmeneno' THEN 'Změna hesla'
            WHEN z ? 'zablokovano_do' AND z -> 'zablokovano_do' -> 'na' <> 'null'
                THEN 'Zablokování po neúspěšných pokusech'
            WHEN z ? 'zablokovano_do' THEN 'Odblokování'
            WHEN z ? 'pozvanka_odeslana' THEN 'Pozvánka'
            ELSE 'Úprava účtu' END
        WHEN 'letadlo' THEN CASE p_operace
            WHEN 'INSERT' THEN 'Založení letadla' WHEN 'DELETE' THEN 'Smazání letadla' ELSE 'Úprava letadla' END
        ELSE p_operace
    END
$$;

-- Popis změny: posádka jako „funkce jméno“, jinak „popisek hodnota“ / „popisek z → na“.
CREATE FUNCTION lkkl.audit_popis(p_tabulka text, p_operace text, z jsonb) RETURNS text
LANGUAGE sql STABLE AS $$
    SELECT CASE
        WHEN p_tabulka = 'posadka' AND p_operace <> 'UPDATE' THEN
            lkkl.audit_hodnota('funkce_id', z -> 'funkce_id') || ' ' || lkkl.audit_hodnota('osoba_id', z -> 'osoba_id')
        ELSE (
            SELECT string_agg(
                CASE
                    WHEN p.skryt_hodnotu THEN p.popisek
                    WHEN p_operace <> 'UPDATE' THEN p.popisek || ' ' || lkkl.audit_hodnota(p.sloupec, z -> p.sloupec)
                    WHEN z -> p.sloupec -> 'z' = 'null' THEN p.popisek || ' ' || lkkl.audit_hodnota(p.sloupec, z -> p.sloupec -> 'na')
                    ELSE p.popisek || ' ' || lkkl.audit_hodnota(p.sloupec, z -> p.sloupec -> 'z')
                         || ' → ' || lkkl.audit_hodnota(p.sloupec, z -> p.sloupec -> 'na')
                END, ', ' ORDER BY p.poradi)
            FROM lkkl.audit_popisek p
            WHERE p.tabulka = p_tabulka AND z ? p.sloupec
              -- u založení a smazání vynechat skryté, prázdné a výchozí „ne“
              AND NOT (p_operace <> 'UPDATE' AND (p.skryt_hodnotu OR z -> p.sloupec IN ('null', 'false')))
        )
    END
$$;

CREATE VIEW lkkl.v_audit AS
SELECT au.id, au.kdy, au.transakce, au.tabulka, au.klic, au.let_id, au.operace,
       CASE WHEN au.zdroj = 'databaze' THEN 'přímo v databázi'
            WHEN o.id IS NULL THEN 'aplikace'
            WHEN p.id IS NOT NULL THEN p.jmeno || ' ' || p.prijmeni || ' (jako ' || o.jmeno || ' ' || o.prijmeni || ')'
            ELSE o.jmeno || ' ' || o.prijmeni
       END AS kdo,
       lkkl.audit_akce(au.tabulka, au.operace, au.zmeny) AS akce,
       lkkl.audit_popis(au.tabulka, au.operace, au.zmeny) AS popis
FROM lkkl.audit au
LEFT JOIN lkkl.osoba o ON o.id = au.osoba_id
LEFT JOIN lkkl.osoba p ON p.id = au.puvodni_osoba_id;
COMMENT ON VIEW lkkl.v_audit IS 'Auditní log čitelně: kdo, akce (odvozená ze změny), popis „popisek z → na“.';

-- Historie letu: změny jedné akce (let + posádka + T&G v jedné transakci) v jednom řádku.
CREATE VIEW lkkl.v_historie_letu AS
SELECT let_id,
       transakce,
       min(kdy) AS kdy,
       min(kdo) AS kdo,
       (array_agg(akce ORDER BY CASE tabulka WHEN 'let' THEN 1 WHEN 'posadka' THEN 2 ELSE 3 END, id))[1] AS akce,
       string_agg(popis, ', ' ORDER BY CASE tabulka WHEN 'let' THEN 1 WHEN 'posadka' THEN 2 ELSE 3 END, id)
           FILTER (WHERE popis IS NOT NULL) AS popis
FROM lkkl.v_audit
WHERE let_id IS NOT NULL
GROUP BY let_id, transakce;
COMMENT ON VIEW lkkl.v_historie_letu IS 'Historie letu pro detail: jedna akce = jeden řádek (seřadit podle kdy).';
