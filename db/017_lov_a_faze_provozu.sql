-- 017: předpona lov_ pro všechna trvalá data a fáze provozu (testování → pilot → ostrý).
--
-- lov_ = trvalá data (číselníky, osoby, letadla, osnovy, popisky auditu a vazby mezi nimi);
-- při zahájení ostrého provozu zůstávají. Provozní data (lety, audit, relace…) se tehdy
-- jednorázově vyprázdní – funkce lkkl.zahajit_ostry_provoz(). Mimo lov_ zůstávají jen
-- technické tabulky ucet, migrace a provoz.

-- --- přejmenování tabulek --------------------------------------------------------------------
-- Pohledy a cizí klíče se odkazují na tabulku, ne na její jméno – přejmenování přežijí.

ALTER TABLE lkkl.letadlo     RENAME TO lov_letadlo;
ALTER TABLE lkkl.osoba       RENAME TO lov_osoba;
ALTER TABLE lkkl.ucel_funkce RENAME TO lov_ucel_funkce;
ALTER TABLE lkkl.osnova_ucel RENAME TO lov_osnova_ucel;
ALTER TABLE lkkl.audit_popisek RENAME TO lov_audit_popisek;

-- Omezení, indexy a sekvence těchto tabulek s předponou starého jména (jako by tak byly od
-- začátku); letadlo_bez_prekryvu patří tabulce let a zůstává.
DO $$
DECLARE
    r record;
BEGIN
    FOR r IN
        SELECT c.conrelid::regclass AS tabulka, c.conname AS jmeno
        FROM pg_constraint c JOIN pg_namespace n ON n.oid = c.connamespace
        WHERE n.nspname = 'lkkl' AND c.conname ~ '^(letadlo|osoba|ucel_funkce|osnova_ucel|audit_popisek)_'
          AND c.conrelid IN ('lkkl.lov_letadlo'::regclass, 'lkkl.lov_osoba'::regclass,
                             'lkkl.lov_ucel_funkce'::regclass, 'lkkl.lov_osnova_ucel'::regclass,
                             'lkkl.lov_audit_popisek'::regclass)
    LOOP
        EXECUTE format('ALTER TABLE %s RENAME CONSTRAINT %I TO %I', r.tabulka, r.jmeno, 'lov_' || r.jmeno);
    END LOOP;
    FOR r IN
        SELECT indexname AS jmeno FROM pg_indexes
        WHERE schemaname = 'lkkl' AND indexname ~ '^(letadlo|osoba|ucel_funkce|osnova_ucel|audit_popisek)_'
          AND tablename IN ('lov_letadlo', 'lov_osoba', 'lov_ucel_funkce', 'lov_osnova_ucel',
                            'lov_audit_popisek')
    LOOP
        EXECUTE format('ALTER INDEX lkkl.%I RENAME TO %I', r.jmeno, 'lov_' || r.jmeno);
    END LOOP;
    FOR r IN
        SELECT sequencename AS jmeno FROM pg_sequences
        WHERE schemaname = 'lkkl' AND sequencename ~ '^(letadlo|osoba)_'
    LOOP
        EXECUTE format('ALTER SEQUENCE lkkl.%I RENAME TO %I', r.jmeno, 'lov_' || r.jmeno);
    END LOOP;
END $$;

ALTER TRIGGER osoba_email_u_uctu ON lkkl.lov_osoba RENAME TO lov_osoba_email_u_uctu;
ALTER FUNCTION lkkl.osoba_email_u_uctu() RENAME TO lov_osoba_email_u_uctu;

-- Funkce mají tělo uložené jako text: odkazy na staré jméno tabulky se v nich přepíšou
-- (lkkl.osoba → lkkl.lov_osoba…) a funkce se znovu založí.
DO $$
DECLARE
    r record;
BEGIN
    FOR r IN
        SELECT p.oid FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'lkkl' AND p.prosrc ~ 'lkkl\.(letadlo|osoba|ucel_funkce|osnova_ucel|audit_popisek)\M'
    LOOP
        EXECUTE regexp_replace(pg_get_functiondef(r.oid),
                               'lkkl\.(letadlo|osoba|ucel_funkce|osnova_ucel|audit_popisek)\M', 'lkkl.lov_\1', 'g');
    END LOOP;
END $$;

-- Audit zapisuje jméno tabulky: popisky, názvy akcí a dosavadní záznamy na nová jména.
-- (Úprava historie jen kvůli přejmenování; ochranu auditu vypne jen tato transakce.)
UPDATE lkkl.lov_audit_popisek SET tabulka = 'lov_' || tabulka WHERE tabulka IN ('letadlo', 'osoba');
ALTER TABLE lkkl.audit DISABLE TRIGGER audit_jen_doplnovat;
UPDATE lkkl.audit SET tabulka = 'lov_' || tabulka WHERE tabulka IN ('letadlo', 'osoba');
ALTER TABLE lkkl.audit ENABLE TRIGGER audit_jen_doplnovat;
DO $$
BEGIN
    EXECUTE regexp_replace(pg_get_functiondef('lkkl.audit_akce(text, text, jsonb)'::regprocedure),
                           'WHEN ''(letadlo|osoba)'' THEN', 'WHEN ''lov_\1'' THEN', 'g');
END $$;

-- Pohled letadel: jeden nabídkový pohled podle standardu (v_lov_<název>) místo dvou.
DROP VIEW lkkl.v_letadlo;
DROP VIEW lkkl.v_letadlo_nabidka;
CREATE VIEW lkkl.v_lov_letadlo AS
SELECT l.id, l.rejstrik, t.nazev AS typ, k.nazev AS kategorie, k.kod AS kategorie_kod,
       t.pocet_mist, l.max_doba_min, l.vlecne, l.soukrome, l.mimo_provoz
FROM lkkl.lov_letadlo l
JOIN lkkl.lov_typ t ON t.id = l.typ_id
JOIN lkkl.lov_kategorie k ON k.id = t.kategorie_id
ORDER BY k.poradi, t.poradi, t.nazev, l.rejstrik;
COMMENT ON VIEW lkkl.v_lov_letadlo IS
    'Letadla pro nabídky a obrazovky: typ, kategorie, počet míst; i mimo provoz (zobrazí se, nejdou vybrat).';

-- --- fáze provozu ----------------------------------------------------------------------------

CREATE TABLE lkkl.provoz (
    jediny  boolean     PRIMARY KEY DEFAULT true CHECK (jediny),
    faze    text        NOT NULL CHECK (faze IN ('testovani', 'pilot', 'ostry')),
    zmeneno timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE lkkl.provoz IS
    'Fáze provozu (jediný řádek): testovani → pilot → ostry. Ostrý provoz zahájí jen '
    'lkkl.zahajit_ostry_provoz(); zpět už nejde.';
INSERT INTO lkkl.provoz (faze) VALUES ('testovani');

-- Tabulky, které se při zahájení ostrého provozu vyprázdní: vše mimo lov_ a technické tabulky.
CREATE VIEW lkkl.v_provozni_tabulky AS
SELECT tablename::text AS tabulka
FROM pg_tables
WHERE schemaname = 'lkkl'
  AND tablename !~ '^lov_'
  AND tablename NOT IN ('ucet', 'migrace', 'provoz')
ORDER BY 1;
COMMENT ON VIEW lkkl.v_provozni_tabulky IS
    'Provozní tabulky – vyprázdní je zahájení ostrého provozu (testovací a pilotní záznamy).';

CREATE FUNCTION lkkl.provoz_zmena() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Fáze provozu se nemaže.';
    END IF;
    IF OLD.faze = 'ostry' THEN
        RAISE EXCEPTION 'Ostrý provoz už nejde vrátit.';
    END IF;
    IF NEW.faze = 'ostry' AND current_setting('lkkl.zahajeni_ostreho_provozu', true) IS DISTINCT FROM 'ano' THEN
        RAISE EXCEPTION 'Ostrý provoz se zahajuje funkcí lkkl.zahajit_ostry_provoz().';
    END IF;
    NEW.zmeneno := now();
    RETURN NEW;
END $$;
CREATE TRIGGER provoz_zmena BEFORE UPDATE OR DELETE ON lkkl.provoz
    FOR EACH ROW EXECUTE FUNCTION lkkl.provoz_zmena();

-- Lety a audit nejde vyprázdnit (TRUNCATE) – jen při zahájení ostrého provozu.
CREATE FUNCTION lkkl.nevyprazdnovat() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF current_setting('lkkl.zahajeni_ostreho_provozu', true) IS DISTINCT FROM 'ano' THEN
        RAISE EXCEPTION 'Tabulka % se nevyprazdňuje (jen při zahájení ostrého provozu).', TG_TABLE_NAME;
    END IF;
    RETURN NULL;
END $$;
DROP TRIGGER audit_bez_vyprazdneni ON lkkl.audit;
CREATE TRIGGER audit_nevyprazdnovat BEFORE TRUNCATE ON lkkl.audit
    FOR EACH STATEMENT EXECUTE FUNCTION lkkl.nevyprazdnovat();
CREATE TRIGGER let_nevyprazdnovat BEFORE TRUNCATE ON lkkl.let
    FOR EACH STATEMENT EXECUTE FUNCTION lkkl.nevyprazdnovat();

CREATE FUNCTION lkkl.zahajit_ostry_provoz() RETURNS text LANGUAGE plpgsql AS $$
DECLARE
    v_tabulky text;
BEGIN
    IF (SELECT faze FROM lkkl.provoz FOR UPDATE) = 'ostry' THEN
        RAISE EXCEPTION 'Ostrý provoz už běží.';
    END IF;
    SELECT string_agg(format('lkkl.%I', tabulka), ', ') INTO v_tabulky FROM lkkl.v_provozni_tabulky;
    PERFORM set_config('lkkl.zahajeni_ostreho_provozu', 'ano', true);
    EXECUTE 'TRUNCATE ' || v_tabulky || ' RESTART IDENTITY';
    UPDATE lkkl.provoz SET faze = 'ostry';
    PERFORM set_config('lkkl.zahajeni_ostreho_provozu', '', true);
    RETURN v_tabulky;
END $$;
COMMENT ON FUNCTION lkkl.zahajit_ostry_provoz() IS
    'Jednorázově vyprázdní provozní tabulky (v_provozni_tabulky, čísla od 1) a nastaví fázi ostry. '
    'Spouští se příkazem python -m app.prikazy ostry-provoz po záloze.';
