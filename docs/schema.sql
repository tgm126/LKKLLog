-- Aktuální schéma lkkl: generuje bash db/schema.sh ze skriptů db/ – neupravovat ručně.
-- Zdrojem pravdy zůstávají skripty db/ (CLAUDE.md 12); tohle je jejich výsledek v jednom souboru.
--
-- PostgreSQL database dump
--



SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: lkkl; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA lkkl;


--
-- Name: kod; Type: DOMAIN; Schema: lkkl; Owner: -
--

CREATE DOMAIN lkkl.kod AS text
	CONSTRAINT kod_check CHECK ((VALUE ~ '^[A-Z0-9_-]+$'::text));


--
-- Name: DOMAIN kod; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON DOMAIN lkkl.kod IS 'Kód položky číselníku: velká písmena, číslice, podtržítko, pomlčka. U řídicích číselníků jen pro program, u evidenčních oficiální označení (zobrazuje se).';


--
-- Name: nazev; Type: DOMAIN; Schema: lkkl; Owner: -
--

CREATE DOMAIN lkkl.nazev AS text
	CONSTRAINT nazev_check CHECK ((btrim(VALUE) <> ''::text));


--
-- Name: DOMAIN nazev; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON DOMAIN lkkl.nazev IS 'Text pro zobrazení v aplikaci; nesmí být prázdný.';


--
-- Name: platny; Type: DOMAIN; Schema: lkkl; Owner: -
--

CREATE DOMAIN lkkl.platny AS boolean DEFAULT true;


--
-- Name: DOMAIN platny; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON DOMAIN lkkl.platny IS 'Položka se používá (nabízí). Neplatná se nenabízí, ale nemaže.';


--
-- Name: poradi; Type: DOMAIN; Schema: lkkl; Owner: -
--

CREATE DOMAIN lkkl.poradi AS smallint DEFAULT 100
	CONSTRAINT poradi_check CHECK ((VALUE >= 0));


--
-- Name: DOMAIN poradi; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON DOMAIN lkkl.poradi IS 'Pořadí v nabídkách (menší = výš).';


--
-- Name: audit_akce(text, text, jsonb); Type: FUNCTION; Schema: lkkl; Owner: -
--

CREATE FUNCTION lkkl.audit_akce(p_tabulka text, p_operace text, z jsonb) RETURNS text
    LANGUAGE sql IMMUTABLE
    AS $$
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
        WHEN 'lov_osoba' THEN CASE p_operace
            WHEN 'INSERT' THEN 'Založení osoby' WHEN 'DELETE' THEN 'Smazání osoby' ELSE 'Úprava osoby' END
        WHEN 'lov_osoba_opravneni' THEN CASE
            WHEN p_operace = 'INSERT' THEN 'Přidání oprávnění'
            WHEN p_operace = 'DELETE' THEN 'Odebrání oprávnění'
            WHEN z -> 'omezene' -> 'na' = 'true' THEN 'Omezení oprávnění'
            WHEN z -> 'omezene' -> 'na' = 'false' THEN 'Zrušení omezení'
            ELSE 'Úprava oprávnění' END
        WHEN 'lov_osoba_opravneni_kategorie' THEN CASE p_operace
            WHEN 'INSERT' THEN 'Oprávnění: přidání kategorie'
            WHEN 'DELETE' THEN 'Oprávnění: odebrání kategorie'
            ELSE 'Úprava oprávnění' END
        WHEN 'ucet' THEN CASE
            WHEN p_operace = 'INSERT' THEN 'Aktivace účtu'
            WHEN p_operace = 'DELETE' THEN 'Zrušení účtu'
            -- přihlášení povoleno / vypnuto (do 039 sloupec aktivni – staré záznamy auditu)
            WHEN coalesce(z -> 'prihlaseni_povoleno', z -> 'aktivni') -> 'na' = 'false' THEN 'Přihlášení vypnuto'
            WHEN coalesce(z -> 'prihlaseni_povoleno', z -> 'aktivni') -> 'na' = 'true' THEN 'Přihlášení povoleno'
            WHEN z ? 'heslo_zmeneno' THEN 'Změna hesla'
            WHEN z ? 'zablokovano_do' AND z -> 'zablokovano_do' -> 'na' <> 'null'
                THEN 'Zablokování po neúspěšných pokusech'
            WHEN z ? 'zablokovano_do' THEN 'Odblokování'
            WHEN z ? 'pozvanka_odeslana' THEN 'Pozvánka'
            ELSE 'Úprava účtu' END
        WHEN 'lov_letadlo' THEN CASE p_operace
            WHEN 'INSERT' THEN 'Založení letadla' WHEN 'DELETE' THEN 'Smazání letadla' ELSE 'Úprava letadla' END
        -- editor výcviku (042)
        WHEN 'lov_osnova' THEN CASE p_operace
            WHEN 'INSERT' THEN 'Založení osnovy' WHEN 'DELETE' THEN 'Smazání osnovy' ELSE 'Úprava osnovy' END
        WHEN 'lov_uloha' THEN CASE p_operace
            WHEN 'INSERT' THEN 'Založení úlohy' WHEN 'DELETE' THEN 'Smazání úlohy' ELSE 'Úprava úlohy' END
        WHEN 'lov_uloha_ucel' THEN CASE p_operace
            WHEN 'INSERT' THEN 'Úloha: přidání účelu' WHEN 'DELETE' THEN 'Úloha: odebrání účelu' ELSE 'Úprava úlohy' END
        WHEN 'lov_prezkouseni' THEN CASE p_operace
            WHEN 'INSERT' THEN 'Založení typu přezkoušení' WHEN 'DELETE' THEN 'Smazání typu přezkoušení'
            ELSE 'Úprava typu přezkoušení' END
        WHEN 'lov_prezkouseni_opravneni' THEN CASE p_operace
            WHEN 'INSERT' THEN 'Přezkoušení: přidání oprávnění' WHEN 'DELETE' THEN 'Přezkoušení: odebrání oprávnění'
            ELSE 'Úprava typu přezkoušení' END
        -- druhy oprávnění a jejich vazby (045)
        WHEN 'lov_opravneni' THEN CASE p_operace
            WHEN 'INSERT' THEN 'Založení druhu oprávnění' WHEN 'DELETE' THEN 'Smazání druhu oprávnění'
            ELSE 'Úprava druhu oprávnění' END
        WHEN 'lov_opravneni_kategorie' THEN CASE p_operace
            WHEN 'INSERT' THEN 'Druh oprávnění: přidání kategorie' WHEN 'DELETE' THEN 'Druh oprávnění: odebrání kategorie'
            ELSE 'Úprava druhu oprávnění' END
        WHEN 'lov_opravneni_role' THEN CASE p_operace
            WHEN 'INSERT' THEN 'Druh oprávnění: přidání role' WHEN 'DELETE' THEN 'Druh oprávnění: odebrání role'
            ELSE 'Úprava druhu oprávnění' END
        ELSE p_operace
    END
$$;


--
-- Name: audit_hodnota(text, jsonb); Type: FUNCTION; Schema: lkkl; Owner: -
--

CREATE FUNCTION lkkl.audit_hodnota(p_sloupec text, p_hodnota jsonb) RETURNS text
    LANGUAGE sql STABLE
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


--
-- Name: audit_jen_doplnovat(); Type: FUNCTION; Schema: lkkl; Owner: -
--

CREATE FUNCTION lkkl.audit_jen_doplnovat() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    RAISE EXCEPTION 'Auditní log jde jen doplňovat.';
END $$;


--
-- Name: audit_popis(text, text, jsonb); Type: FUNCTION; Schema: lkkl; Owner: -
--

CREATE FUNCTION lkkl.audit_popis(p_tabulka text, p_operace text, z jsonb) RETURNS text
    LANGUAGE sql STABLE
    AS $$
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
            FROM lkkl.lov_audit_popisek p
            WHERE p.tabulka = p_tabulka AND z ? p.sloupec
              -- u založení a smazání vynechat skryté, prázdné a výchozí „ne“
              AND NOT (p_operace <> 'UPDATE' AND (p.skryt_hodnotu OR z -> p.sloupec IN ('null', 'false')))
        )
    END
$$;


--
-- Name: audit_zapsat(); Type: FUNCTION; Schema: lkkl; Owner: -
--

CREATE FUNCTION lkkl.audit_zapsat() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
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


--
-- Name: cas_hlasky(timestamp with time zone); Type: FUNCTION; Schema: lkkl; Owner: -
--

CREATE FUNCTION lkkl.cas_hlasky(p_cas timestamp with time zone) RETURNS text
    LANGUAGE sql STABLE
    AS $$
    SELECT to_char(p_cas AT TIME ZONE 'UTC',
                   CASE WHEN (p_cas AT TIME ZONE 'UTC')::date = (now() AT TIME ZONE 'UTC')::date
                        THEN 'HH24:MI' ELSE 'FMDD. FMMM. HH24:MI' END)
$$;


--
-- Name: FUNCTION cas_hlasky(p_cas timestamp with time zone); Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON FUNCTION lkkl.cas_hlasky(p_cas timestamp with time zone) IS 'Čas v UTC do chybové hlášky (jiný den i s datem).';


--
-- Name: cas_ne_v_budoucnosti(); Type: FUNCTION; Schema: lkkl; Owner: -
--

CREATE FUNCTION lkkl.cas_ne_v_budoucnosti() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
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


--
-- Name: doba_letu_min(timestamp with time zone, timestamp with time zone); Type: FUNCTION; Schema: lkkl; Owner: -
--

CREATE FUNCTION lkkl.doba_letu_min(p_vzlet timestamp with time zone, p_pristani timestamp with time zone) RETURNS integer
    LANGUAGE sql IMMUTABLE PARALLEL SAFE
    RETURN CASE WHEN (p_pristani IS NOT NULL) THEN (GREATEST((1)::numeric, floor(((EXTRACT(epoch FROM (p_pristani - p_vzlet)) + (30)::numeric) / (60)::numeric))))::integer ELSE NULL::integer END;


--
-- Name: FUNCTION doba_letu_min(p_vzlet timestamp with time zone, p_pristani timestamp with time zone); Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON FUNCTION lkkl.doba_letu_min(p_vzlet timestamp with time zone, p_pristani timestamp with time zone) IS 'Doba letu v celých minutách z naměřených časů: čistý čas zaokrouhlený (30 s a víc nahoru), nejméně 1 minuta; bez přistání prázdná.';


--
-- Name: kontrola_platnosti(); Type: FUNCTION; Schema: lkkl; Owner: -
--

CREATE FUNCTION lkkl.kontrola_platnosti() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
DECLARE
    sloupec text := TG_ARGV[0];
    tabulka text := TG_ARGV[1];
    nova bigint := (to_jsonb(NEW) ->> sloupec)::bigint;
    plati boolean;
    nazev text;
BEGIN
    IF nova IS NULL
       OR (TG_OP = 'UPDATE' AND nova IS NOT DISTINCT FROM (to_jsonb(OLD) ->> sloupec)::bigint) THEN
        RETURN NEW;
    END IF;
    EXECUTE format(
        $q$SELECT t.platny,
                  coalesce(j ->> 'nazev', j ->> 'rejstrik', (j ->> 'jmeno') || ' ' || (j ->> 'prijmeni'))
           FROM lkkl.%I t, to_jsonb(t) j WHERE t.id = $1$q$, tabulka)
        INTO plati, nazev USING nova;
    IF plati IS FALSE THEN
        RAISE EXCEPTION '% „%“ už neplatí – nejde použít.', TG_ARGV[2], nazev;
    END IF;
    RETURN NEW;
END $_$;


--
-- Name: FUNCTION kontrola_platnosti(); Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON FUNCTION lkkl.kontrola_platnosti() IS 'Trigger: nová nebo změněná vazba nesmí vést na neplatný záznam lov_ (sloupec, tabulka, popis).';


--
-- Name: let_doplnit_misto(); Type: FUNCTION; Schema: lkkl; Owner: -
--

CREATE FUNCTION lkkl.let_doplnit_misto() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_domovske bigint := (SELECT id FROM lkkl.lov_letiste WHERE domovske);
BEGIN
    IF NEW.misto_vzletu_id IS NULL AND NEW.misto_vzletu_popis IS NULL THEN
        NEW.misto_vzletu_id := v_domovske;
    END IF;
    IF NEW.misto_pristani_id IS NULL AND NEW.misto_pristani_popis IS NULL THEN
        NEW.misto_pristani_id := v_domovske;
    END IF;
    RETURN NEW;
END $$;


--
-- Name: let_kontrola(); Type: FUNCTION; Schema: lkkl; Owner: -
--

CREATE FUNCTION lkkl.let_kontrola() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF TG_TABLE_NAME = 'let' THEN
        PERFORM lkkl.let_zkontrolovat(NEW.id);
        PERFORM lkkl.let_osoby_bez_prekryvu(NEW.id);
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
            PERFORM lkkl.let_osoby_bez_prekryvu(NEW.let_id);
        END IF;
    END IF;
    RETURN NULL;
END $$;


--
-- Name: let_letadlo_volne(); Type: FUNCTION; Schema: lkkl; Owner: -
--

CREATE FUNCTION lkkl.let_letadlo_volne() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
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


--
-- Name: FUNCTION let_letadlo_volne(); Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON FUNCTION lkkl.let_letadlo_volne() IS 'Letadlo nesmí mít dva překrývající se lety – hláška s údaji druhého letu.';


--
-- Name: let_nemazat(); Type: FUNCTION; Schema: lkkl; Owner: -
--

CREATE FUNCTION lkkl.let_nemazat() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF current_setting('lkkl.mazani_letu_dne', true) IS DISTINCT FROM 'ano' THEN
        RAISE EXCEPTION 'Let se nemaže, jen se zruší s důvodem (celý den smaže admin: CALL lkkl.smazat_lety_dne(den)).';
    END IF;
    RETURN OLD;
END $$;


--
-- Name: let_osoby_bez_prekryvu(bigint); Type: FUNCTION; Schema: lkkl; Owner: -
--

CREATE FUNCTION lkkl.let_osoby_bez_prekryvu(p_let_id bigint) RETURNS void
    LANGUAGE plpgsql
    AS $$
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


--
-- Name: FUNCTION let_osoby_bez_prekryvu(p_let_id bigint); Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON FUNCTION lkkl.let_osoby_bez_prekryvu(p_let_id bigint) IS 'Osoba na palubě (PIC, žák, přezkoušený) nesmí být ve vzduchu ve dvou letech zároveň.';


--
-- Name: let_popis_hlasky(bigint, bigint); Type: FUNCTION; Schema: lkkl; Owner: -
--

CREATE FUNCTION lkkl.let_popis_hlasky(p_let_id bigint, p_krome_osoby bigint DEFAULT NULL::bigint) RETURNS text
    LANGUAGE sql STABLE
    AS $$
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


--
-- Name: let_verze(); Type: FUNCTION; Schema: lkkl; Owner: -
--

CREATE FUNCTION lkkl.let_verze() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.verze := OLD.verze + 1;
    RETURN NEW;
END $$;


--
-- Name: let_zkontrolovat(bigint); Type: FUNCTION; Schema: lkkl; Owner: -
--

CREATE FUNCTION lkkl.let_zkontrolovat(p_let_id bigint) RETURNS void
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


--
-- Name: lov_osoba_email_u_uctu(); Type: FUNCTION; Schema: lkkl; Owner: -
--

CREATE FUNCTION lkkl.lov_osoba_email_u_uctu() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NEW.email IS NULL AND EXISTS (SELECT 1 FROM lkkl.ucet WHERE osoba_id = NEW.id) THEN
        RAISE EXCEPTION 'Osoba % má účet, e-mail nejde smazat.', NEW.id;
    END IF;
    RETURN NEW;
END $$;


--
-- Name: na_minuty(timestamp with time zone); Type: FUNCTION; Schema: lkkl; Owner: -
--

CREATE FUNCTION lkkl.na_minuty(p_cas timestamp with time zone) RETURNS timestamp with time zone
    LANGUAGE sql IMMUTABLE PARALLEL SAFE
    RETURN to_timestamp((((946684800)::numeric + (floor(((EXTRACT(epoch FROM (p_cas - '2000-01-01 00:00:00+00'::timestamp with time zone)) + (30)::numeric) / (60)::numeric)) * (60)::numeric)))::double precision);


--
-- Name: FUNCTION na_minuty(p_cas timestamp with time zone); Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON FUNCTION lkkl.na_minuty(p_cas timestamp with time zone) IS 'Čas zaokrouhlený na nejbližší celou minutu (od 30 s nahoru).';


--
-- Name: nevyprazdnovat(); Type: FUNCTION; Schema: lkkl; Owner: -
--

CREATE FUNCTION lkkl.nevyprazdnovat() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    RAISE EXCEPTION 'Tabulka % se nevyprazdňuje.', TG_TABLE_NAME;
END $$;


--
-- Name: pristani_na_minuty(timestamp with time zone, timestamp with time zone); Type: FUNCTION; Schema: lkkl; Owner: -
--

CREATE FUNCTION lkkl.pristani_na_minuty(p_vzlet timestamp with time zone, p_pristani timestamp with time zone) RETURNS timestamp with time zone
    LANGUAGE sql IMMUTABLE PARALLEL SAFE
    RETURN to_timestamp(((((946684800)::numeric + EXTRACT(epoch FROM (lkkl.na_minuty(p_vzlet) - '2000-01-01 00:00:00+00'::timestamp with time zone))) + ((60 * lkkl.doba_letu_min(p_vzlet, p_pristani)))::numeric))::double precision);


--
-- Name: FUNCTION pristani_na_minuty(p_vzlet timestamp with time zone, p_pristani timestamp with time zone); Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON FUNCTION lkkl.pristani_na_minuty(p_vzlet timestamp with time zone, p_pristani timestamp with time zone) IS 'Přistání na minuty = vzlet na minuty + doba; bez přistání prázdné.';


--
-- Name: smazat_lety_dne(date, integer); Type: PROCEDURE; Schema: lkkl; Owner: -
--

CREATE PROCEDURE lkkl.smazat_lety_dne(IN p_den date, INOUT smazano integer DEFAULT NULL::integer)
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_lety bigint[];
BEGIN
    IF p_den IS NULL THEN
        RAISE EXCEPTION 'Zadejte den (RRRR-MM-DD).';
    END IF;
    -- lety dne a k nim druhá polovina vleku (vlečná i kluzák)
    SELECT array_agg(DISTINCT x.id) INTO v_lety
    FROM (
        SELECT l.id FROM lkkl.let l
        WHERE (coalesce(l.cas_vzletu, l.zalozeno) AT TIME ZONE 'UTC')::date = p_den
        UNION
        SELECT l.vlecny_let_id FROM lkkl.let l
        WHERE (coalesce(l.cas_vzletu, l.zalozeno) AT TIME ZONE 'UTC')::date = p_den
          AND l.vlecny_let_id IS NOT NULL
        UNION
        SELECT k.id FROM lkkl.let k JOIN lkkl.let v ON v.id = k.vlecny_let_id
        WHERE (coalesce(v.cas_vzletu, v.zalozeno) AT TIME ZONE 'UTC')::date = p_den
    ) x;
    smazano := coalesce(cardinality(v_lety), 0);
    IF smazano = 0 THEN
        RAISE NOTICE 'Dne % žádný let není.', p_den;
        RETURN;
    END IF;

    PERFORM set_config('lkkl.mazani_letu_dne', 'ano', true);
    -- kontrola letu po odebrání posádky a T&G až na konci transakce (let už nebude, kontrola
    -- ho přeskočí) – i když volající kontroly přepnul na okamžité
    SET CONSTRAINTS lkkl.posadka_kontrola, lkkl.let_tg_kontrola DEFERRED;
    DELETE FROM lkkl.let_tg WHERE let_id = ANY (v_lety);
    DELETE FROM lkkl.posadka WHERE let_id = ANY (v_lety);
    DELETE FROM lkkl.let WHERE id = ANY (v_lety);  -- kluzák i jeho vlečná jedním příkazem
    PERFORM set_config('lkkl.mazani_letu_dne', '', true);
    RAISE NOTICE 'Smazáno letů dne %: %.', p_den, smazano;
END $$;


--
-- Name: PROCEDURE smazat_lety_dne(IN p_den date, INOUT smazano integer); Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON PROCEDURE lkkl.smazat_lety_dne(IN p_den date, INOUT smazano integer) IS 'Admin: smaže všechny lety dne (datum vzletu, jinak založení; UTC) s posádkou a T&G, u vleku celou dvojici; vrátí počet. Audit zůstává. CALL lkkl.smazat_lety_dne(''RRRR-MM-DD'');';


--
-- Name: ucet_osoba_ma_email(); Type: FUNCTION; Schema: lkkl; Owner: -
--

CREATE FUNCTION lkkl.ucet_osoba_ma_email() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_email text;
BEGIN
    SELECT email INTO v_email FROM lkkl.lov_osoba WHERE id = NEW.osoba_id;
    IF FOUND AND v_email IS NULL THEN
        RAISE EXCEPTION 'Účet může mít jen osoba s e-mailem (osoba %).', NEW.osoba_id;
    END IF;
    RETURN NEW;
END $$;


--
-- Name: vlek_zkontrolovat(bigint); Type: FUNCTION; Schema: lkkl; Owner: -
--

CREATE FUNCTION lkkl.vlek_zkontrolovat(p_kluzak bigint) RETURNS void
    LANGUAGE plpgsql
    AS $$
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


--
-- Name: FUNCTION vlek_zkontrolovat(p_kluzak bigint); Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON FUNCTION lkkl.vlek_zkontrolovat(p_kluzak bigint) IS 'Kontrola dvojice vleku (z let_zkontrolovat): stejný vzlet, zrušení před vzletem celé, vlekař mimo posádku kluzáku.';


--
-- Name: vycvik_kontrola(); Type: FUNCTION; Schema: lkkl; Owner: -
--

CREATE FUNCTION lkkl.vycvik_kontrola() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_letu integer;
    v_text text;
BEGIN
    IF TG_TABLE_NAME = 'lov_osnova' THEN
        IF NEW.kategorie_id IS DISTINCT FROM OLD.kategorie_id AND EXISTS (
            SELECT 1 FROM lkkl.let l JOIN lkkl.lov_uloha u ON u.id = l.uloha_id
            WHERE u.osnova_id = NEW.id) THEN
            RAISE EXCEPTION 'Osnova „%“ má úlohy v letech – kategorii nejde změnit.', OLD.kod;
        END IF;
    ELSIF TG_TABLE_NAME = 'lov_uloha' THEN
        IF NEW.osnova_id IS DISTINCT FROM OLD.osnova_id
           AND (SELECT kategorie_id FROM lkkl.lov_osnova WHERE id = NEW.osnova_id)
               IS DISTINCT FROM (SELECT kategorie_id FROM lkkl.lov_osnova WHERE id = OLD.osnova_id)
           AND EXISTS (SELECT 1 FROM lkkl.let WHERE uloha_id = NEW.id) THEN
            RAISE EXCEPTION 'Úloha „%“ je použita v letech – do osnovy jiné kategorie ji nejde přesunout.', OLD.nazev;
        END IF;
    ELSIF TG_TABLE_NAME = 'lov_uloha_ucel' THEN
        SELECT count(*) INTO v_letu FROM lkkl.let WHERE uloha_id = OLD.uloha_id AND ucel_id = OLD.ucel_id;
        IF v_letu > 0 THEN
            SELECT o.kod || '/' || u.kod INTO v_text FROM lkkl.lov_uloha u
            JOIN lkkl.lov_osnova o ON o.id = u.osnova_id WHERE u.id = OLD.uloha_id;
            RAISE EXCEPTION 'Úloha % je s účelem „%“ v % letech – účel nejde odebrat (úlohu jde zneplatnit).',
                v_text, (SELECT nazev FROM lkkl.lov_ucel WHERE id = OLD.ucel_id), v_letu;
        END IF;
        RETURN OLD;
    ELSIF TG_TABLE_NAME = 'lov_prezkouseni' THEN
        IF NEW.kategorie_id IS DISTINCT FROM OLD.kategorie_id THEN
            IF EXISTS (SELECT 1 FROM lkkl.let WHERE prezkouseni_id = NEW.id) THEN
                RAISE EXCEPTION 'Typ přezkoušení „%“ je použit v letech – kategorii nejde změnit.', OLD.kod;
            END IF;
            IF EXISTS (SELECT 1 FROM lkkl.lov_prezkouseni_opravneni po
                       WHERE po.prezkouseni_id = NEW.id
                         AND NOT EXISTS (SELECT 1 FROM lkkl.lov_opravneni_kategorie ok
                                         WHERE ok.opravneni_id = po.opravneni_id
                                           AND ok.kategorie_id = NEW.kategorie_id)) THEN
                RAISE EXCEPTION 'Typ přezkoušení „%“ má oprávnění, které se pro novou kategorii nevydává.', OLD.kod;
            END IF;
        END IF;
    ELSIF TG_TABLE_NAME = 'lov_prezkouseni_opravneni' THEN
        IF NOT EXISTS (SELECT 1 FROM lkkl.lov_opravneni_kategorie ok
                       JOIN lkkl.lov_prezkouseni p ON p.kategorie_id = ok.kategorie_id
                       WHERE p.id = NEW.prezkouseni_id AND ok.opravneni_id = NEW.opravneni_id) THEN
            RAISE EXCEPTION 'Oprávnění „%“ se pro kategorii typu přezkoušení nevydává.',
                (SELECT nazev FROM lkkl.lov_opravneni WHERE id = NEW.opravneni_id);
        END IF;
    END IF;
    RETURN NEW;
END $$;


--
-- Name: FUNCTION vycvik_kontrola(); Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON FUNCTION lkkl.vycvik_kontrola() IS 'Pravidla editoru výcviku (042): změna kategorie nebo účelu nesmí rozbít staré lety; typ přezkoušení jen s oprávněním pro jeho kategorii.';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: audit; Type: TABLE; Schema: lkkl; Owner: -
--

CREATE TABLE lkkl.audit (
    id bigint NOT NULL,
    kdy timestamp with time zone DEFAULT now() NOT NULL,
    transakce bigint DEFAULT ((pg_current_xact_id())::text)::bigint NOT NULL,
    tabulka text NOT NULL,
    klic jsonb NOT NULL,
    operace text NOT NULL,
    zmeny jsonb NOT NULL,
    zdroj text NOT NULL,
    osoba_id bigint,
    puvodni_osoba_id bigint,
    db_uzivatel text DEFAULT SESSION_USER NOT NULL,
    let_id bigint GENERATED ALWAYS AS (
CASE
    WHEN (tabulka = 'let'::text) THEN ((klic ->> 'id'::text))::bigint
    WHEN (tabulka = ANY (ARRAY['posadka'::text, 'let_tg'::text])) THEN ((klic ->> 'let_id'::text))::bigint
    ELSE NULL::bigint
END) STORED,
    CONSTRAINT audit_operace_check CHECK ((operace = ANY (ARRAY['INSERT'::text, 'UPDATE'::text, 'DELETE'::text]))),
    CONSTRAINT audit_zdroj_check CHECK ((zdroj = ANY (ARRAY['aplikace'::text, 'databaze'::text])))
);


--
-- Name: TABLE audit; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON TABLE lkkl.audit IS 'Auditní log: kdo, kdy a co změnil. Jen doplňovat. Čitelně: v_audit, v_historie_letu.';


--
-- Name: COLUMN audit.transakce; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.audit.transakce IS 'Číslo transakce – změny jedné akce (let + posádka) mají stejné.';


--
-- Name: COLUMN audit.klic; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.audit.klic IS 'Primární klíč změněného řádku, např. {"id": 15} nebo {"let_id": 15, "osoba_id": 3}.';


--
-- Name: COLUMN audit.zmeny; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.audit.zmeny IS 'INSERT: nový řádek, DELETE: starý řádek, UPDATE: jen změněné sloupce {"sloupec": {"z": …, "na": …}}.';


--
-- Name: COLUMN audit.zdroj; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.audit.zdroj IS 'aplikace, nebo databaze (přímá úprava).';


--
-- Name: COLUMN audit.let_id; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.audit.let_id IS 'Let, ke kterému změna patří (let, posádka, T&G) – pro historii letu.';


--
-- Name: audit_id_seq; Type: SEQUENCE; Schema: lkkl; Owner: -
--

ALTER TABLE lkkl.audit ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME lkkl.audit_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: email; Type: TABLE; Schema: lkkl; Owner: -
--

CREATE TABLE lkkl.email (
    id bigint NOT NULL,
    kdy timestamp with time zone DEFAULT now() NOT NULL,
    druh text NOT NULL,
    osoba_id bigint NOT NULL,
    adresa text NOT NULL,
    odeslal_id bigint NOT NULL,
    chyba text,
    CONSTRAINT email_adresa_check CHECK ((btrim(adresa) <> ''::text)),
    CONSTRAINT email_chyba_check CHECK ((btrim(chyba) <> ''::text)),
    CONSTRAINT email_druh_check CHECK ((druh = 'ODKAZ_HESLO'::text))
);


--
-- Name: TABLE email; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON TABLE lkkl.email IS 'Odeslané e-maily (bez obsahu): druh, komu (osoba a adresa v tu chvíli), kdo poslal, kdy; chyba prázdná = odesláno, jinak text chyby SMTP.';


--
-- Name: COLUMN email.druh; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.email.druh IS 'ODKAZ_HESLO = odkaz pro nastavení hesla.';


--
-- Name: email_id_seq; Type: SEQUENCE; Schema: lkkl; Owner: -
--

ALTER TABLE lkkl.email ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME lkkl.email_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: let; Type: TABLE; Schema: lkkl; Owner: -
--

CREATE TABLE lkkl.let (
    id bigint NOT NULL,
    letadlo_id bigint NOT NULL,
    ucel_id bigint,
    zpusob_vzletu_id bigint NOT NULL,
    vlecny_let_id bigint,
    misto_vzletu_id bigint,
    misto_vzletu_popis text,
    misto_pristani_id bigint,
    misto_pristani_popis text,
    vzlet_namereno timestamp with time zone,
    pristani_namereno timestamp with time zone,
    doba_min integer GENERATED ALWAYS AS (lkkl.doba_letu_min(vzlet_namereno, pristani_namereno)) STORED,
    pocet_pristani smallint,
    pob smallint,
    platce_id bigint,
    plati_aeroklub boolean DEFAULT false NOT NULL,
    poznamka text,
    zruseni_duvod_id bigint,
    zruseno timestamp with time zone,
    zrusil_id bigint,
    zalozil_id bigint NOT NULL,
    zalozeno timestamp with time zone DEFAULT now() NOT NULL,
    verze integer DEFAULT 1 NOT NULL,
    uloha_id bigint,
    prezkouseni_id bigint,
    cas_vzletu timestamp with time zone GENERATED ALWAYS AS (lkkl.na_minuty(vzlet_namereno)) STORED,
    cas_pristani timestamp with time zone GENERATED ALWAYS AS (lkkl.pristani_na_minuty(vzlet_namereno, pristani_namereno)) STORED,
    CONSTRAINT let_misto_pristani_popis_check CHECK ((btrim(misto_pristani_popis) <> ''::text)),
    CONSTRAINT let_misto_vzletu_popis_check CHECK ((btrim(misto_vzletu_popis) <> ''::text)),
    CONSTRAINT let_pob_check CHECK (((pob >= 1) AND (pob <= 20))),
    CONSTRAINT let_poznamka_check CHECK ((btrim(poznamka) <> ''::text)),
    CONSTRAINT misto_pristani_jedno CHECK (((misto_pristani_id IS NULL) <> (misto_pristani_popis IS NULL))),
    CONSTRAINT misto_vzletu_jedno CHECK (((misto_vzletu_id IS NULL) <> (misto_vzletu_popis IS NULL))),
    CONSTRAINT neni_vlastni_vlek CHECK ((vlecny_let_id <> id)),
    CONSTRAINT pocet_pristani_po_pristani CHECK ((((pristani_namereno IS NULL) AND (pocet_pristani IS NULL)) OR ((pristani_namereno IS NOT NULL) AND (pocet_pristani >= 1)))),
    CONSTRAINT prave_jeden_platce CHECK ((plati_aeroklub = (platce_id IS NULL))),
    CONSTRAINT pristani_po_vzletu CHECK (((pristani_namereno IS NULL) OR ((vzlet_namereno IS NOT NULL) AND (pristani_namereno >= vzlet_namereno)))),
    CONSTRAINT zruseni_uplne CHECK ((((zruseni_duvod_id IS NULL) = (zruseno IS NULL)) AND ((zrusil_id IS NULL) OR (zruseno IS NOT NULL))))
);


--
-- Name: TABLE let; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON TABLE lkkl.let IS 'Let. Stav se odvodí (v_let): bez vzletu = naplánovaný, vzlet bez přistání = ve vzduchu, obojí = ukončený, důvod zrušení = zrušený.';


--
-- Name: COLUMN let.ucel_id; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.let.ucel_id IS 'Prázdné právě u vlečného letu (vlek se odvodí z vazby).';


--
-- Name: COLUMN let.vlecny_let_id; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.let.vlecny_let_id IS 'U kluzáku vzlétajícího aerovlekem: let vlečného letadla.';


--
-- Name: COLUMN let.misto_vzletu_id; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.let.misto_vzletu_id IS 'Nezadané doplní trigger domovským letištěm.';


--
-- Name: COLUMN let.misto_vzletu_popis; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.let.misto_vzletu_popis IS 'Místo mimo letiště (terén); jinak misto_vzletu_id.';


--
-- Name: COLUMN let.misto_pristani_id; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.let.misto_pristani_id IS 'Místo přistání (letiště); do přistání plán (cíl), po přistání skutečnost.';


--
-- Name: COLUMN let.misto_pristani_popis; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.let.misto_pristani_popis IS 'Přistání do terénu (popis místa); jinak misto_pristani_id.';


--
-- Name: COLUMN let.vzlet_namereno; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.let.vzlet_namereno IS 'Naměřený vzlet (UTC, na sekundy – určuje server); ručně zadaný na celé minuty. Jinde než v kontrolách a stopkách se nepoužívá – čte se cas_vzletu.';


--
-- Name: COLUMN let.pristani_namereno; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.let.pristani_namereno IS 'Naměřené přistání (UTC, na sekundy – určuje server); ručně zadané na celé minuty. Jinde než v kontrolách se nepoužívá – čte se cas_pristani.';


--
-- Name: COLUMN let.doba_min; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.let.doba_min IS 'Doba letu v celých minutách: čistý naměřený čas zaokrouhlený (30 s a víc nahoru), nejméně 1 minuta; = cas_pristani − cas_vzletu.';


--
-- Name: COLUMN let.pocet_pristani; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.let.pocet_pristani IS 'Počet přistání včetně posledního (T&G = počet − 1); vyplní se při přistání.';


--
-- Name: COLUMN let.pob; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.let.pob IS 'Počet osob na palubě celkem; zadává se jen u účelů bez funkcí (normální let, vlek). U výcviku, sóla a přezkoušení prázdné – odvodí se z posádky (v_let.pob).';


--
-- Name: COLUMN let.verze; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.let.verze IS 'Číslo verze záznamu – chrání opravu před přepsáním souběžnou změnou; zvyšuje trigger.';


--
-- Name: COLUMN let.uloha_id; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.let.uloha_id IS 'Úloha z osnovy; povinnost podle účelu, kontrola v let_zkontrolovat.';


--
-- Name: COLUMN let.prezkouseni_id; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.let.prezkouseni_id IS 'Typ přezkoušení – právě u účelu Přezkoušení (povinný, když pro kategorii letadla nějaký je); úloha se pak nezadává.';


--
-- Name: COLUMN let.cas_vzletu; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.let.cas_vzletu IS 'Vzlet na minuty (UTC): naměřený zaokrouhlený na nejbližší minutu.';


--
-- Name: COLUMN let.cas_pristani; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.let.cas_pristani IS 'Přistání na minuty (UTC) = cas_vzletu + doba_min.';


--
-- Name: let_id_seq; Type: SEQUENCE; Schema: lkkl; Owner: -
--

ALTER TABLE lkkl.let ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME lkkl.let_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: let_tg; Type: TABLE; Schema: lkkl; Owner: -
--

CREATE TABLE lkkl.let_tg (
    let_id bigint NOT NULL,
    cas timestamp with time zone NOT NULL
);


--
-- Name: TABLE let_tg; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON TABLE lkkl.let_tg IS 'Časy jednotlivých touch-and-go (nepovinné; dopsané lety je nemají).';


--
-- Name: lov_audit_popisek; Type: TABLE; Schema: lkkl; Owner: -
--

CREATE TABLE lkkl.lov_audit_popisek (
    tabulka text NOT NULL,
    sloupec text NOT NULL,
    popisek text NOT NULL,
    poradi smallint NOT NULL,
    skryt_hodnotu boolean DEFAULT false NOT NULL
);


--
-- Name: TABLE lov_audit_popisek; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON TABLE lkkl.lov_audit_popisek IS 'Popisky sloupců v čitelné historii a jejich pořadí. Sloupec bez popisku se neukazuje.';


--
-- Name: COLUMN lov_audit_popisek.skryt_hodnotu; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.lov_audit_popisek.skryt_hodnotu IS 'Ukáže se jen, že se změnilo (heslo, telefon); popisek je pak celá věta.';


--
-- Name: lov_duvod_zruseni; Type: TABLE; Schema: lkkl; Owner: -
--

CREATE TABLE lkkl.lov_duvod_zruseni (
    id bigint NOT NULL,
    kod lkkl.kod NOT NULL,
    nazev lkkl.nazev NOT NULL,
    poradi lkkl.poradi NOT NULL,
    platny lkkl.platny NOT NULL
);


--
-- Name: TABLE lov_duvod_zruseni; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON TABLE lkkl.lov_duvod_zruseni IS 'Důvod zrušení letu (let se nemaže).';


--
-- Name: lov_duvod_zruseni_id_seq; Type: SEQUENCE; Schema: lkkl; Owner: -
--

ALTER TABLE lkkl.lov_duvod_zruseni ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME lkkl.lov_duvod_zruseni_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: lov_funkce; Type: TABLE; Schema: lkkl; Owner: -
--

CREATE TABLE lkkl.lov_funkce (
    id bigint NOT NULL,
    kod lkkl.kod NOT NULL,
    nazev lkkl.nazev NOT NULL,
    poradi lkkl.poradi NOT NULL,
    platny lkkl.platny NOT NULL,
    na_palube boolean DEFAULT true NOT NULL
);


--
-- Name: TABLE lov_funkce; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON TABLE lkkl.lov_funkce IS 'Funkce osoby jmenovitě uvedené u letu; ostatní lidé na palubě jsou jen v POB.';


--
-- Name: COLUMN lov_funkce.na_palube; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.lov_funkce.na_palube IS 'Osoba je v letadle (počítá se do POB). Dozor je na zemi.';


--
-- Name: lov_funkce_id_seq; Type: SEQUENCE; Schema: lkkl; Owner: -
--

ALTER TABLE lkkl.lov_funkce ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME lkkl.lov_funkce_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: lov_kategorie; Type: TABLE; Schema: lkkl; Owner: -
--

CREATE TABLE lkkl.lov_kategorie (
    id bigint NOT NULL,
    nazev lkkl.nazev NOT NULL,
    kod lkkl.kod NOT NULL,
    poradi lkkl.poradi NOT NULL,
    platny lkkl.platny NOT NULL
);


--
-- Name: TABLE lov_kategorie; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON TABLE lkkl.lov_kategorie IS 'Kategorie letadel (kluzák, motorový kluzák, letoun, ultralehký letoun).';


--
-- Name: lov_kategorie_id_seq; Type: SEQUENCE; Schema: lkkl; Owner: -
--

ALTER TABLE lkkl.lov_kategorie ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME lkkl.lov_kategorie_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: lov_letadlo; Type: TABLE; Schema: lkkl; Owner: -
--

CREATE TABLE lkkl.lov_letadlo (
    id bigint NOT NULL,
    rejstrik text NOT NULL,
    typ_id bigint NOT NULL,
    soukrome boolean DEFAULT false NOT NULL,
    max_doba_min integer,
    vlecne boolean DEFAULT false NOT NULL,
    mimo_provoz boolean DEFAULT false NOT NULL,
    platny lkkl.platny NOT NULL,
    CONSTRAINT lov_letadlo_max_doba_min_check CHECK ((max_doba_min > 0)),
    CONSTRAINT lov_letadlo_rejstrik_check CHECK (((rejstrik <> ''::text) AND (rejstrik = upper(btrim(rejstrik)))))
);


--
-- Name: TABLE lov_letadlo; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON TABLE lkkl.lov_letadlo IS 'Letadla klubu i soukromá.';


--
-- Name: COLUMN lov_letadlo.rejstrik; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.lov_letadlo.rejstrik IS 'Rejstříková značka, např. OK-3819; ultralehká s mezerou (OK-CUO 78).';


--
-- Name: COLUMN lov_letadlo.soukrome; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.lov_letadlo.soukrome IS 'Soukromé letadlo (vlastník není klub).';


--
-- Name: COLUMN lov_letadlo.max_doba_min; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.lov_letadlo.max_doba_min IS 'Maximální doba letu v minutách; prázdné = nezadáno.';


--
-- Name: COLUMN lov_letadlo.vlecne; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.lov_letadlo.vlecne IS 'Letadlo může vlekat kluzáky.';


--
-- Name: COLUMN lov_letadlo.mimo_provoz; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.lov_letadlo.mimo_provoz IS 'Letadlo se nenabízí pro nové lety (prodané, oprava, porucha); stará data zůstávají.';


--
-- Name: COLUMN lov_letadlo.platny; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.lov_letadlo.platny IS 'Ne = vyřazené (prodané, zrušené): nikde se neukazuje, nejde nově použít; zůstává kvůli historii letů. Dočasný stav je mimo_provoz.';


--
-- Name: lov_letadlo_id_seq; Type: SEQUENCE; Schema: lkkl; Owner: -
--

ALTER TABLE lkkl.lov_letadlo ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME lkkl.lov_letadlo_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: lov_letiste; Type: TABLE; Schema: lkkl; Owner: -
--

CREATE TABLE lkkl.lov_letiste (
    id bigint NOT NULL,
    kod lkkl.kod NOT NULL,
    nazev lkkl.nazev NOT NULL,
    domovske boolean DEFAULT false NOT NULL,
    zem_sirka numeric(8,5),
    zem_delka numeric(8,5),
    nadm_vyska_ft integer,
    poradi lkkl.poradi NOT NULL,
    platny lkkl.platny NOT NULL,
    rychla_volba boolean DEFAULT false NOT NULL,
    CONSTRAINT lov_letiste_kod_icao CHECK (((kod)::text ~ '^[A-Z]{4}$'::text)),
    CONSTRAINT lov_letiste_zem_delka_check CHECK (((zem_delka >= ('-180'::integer)::numeric) AND (zem_delka <= (180)::numeric))),
    CONSTRAINT lov_letiste_zem_sirka_check CHECK (((zem_sirka >= ('-90'::integer)::numeric) AND (zem_sirka <= (90)::numeric)))
);


--
-- Name: TABLE lov_letiste; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON TABLE lkkl.lov_letiste IS 'Letiště a plochy (i bez kódu ICAO).';


--
-- Name: COLUMN lov_letiste.kod; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.lov_letiste.kod IS 'Kód ICAO (4 velká písmena) – zároveň kód číselníku.';


--
-- Name: COLUMN lov_letiste.domovske; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.lov_letiste.domovske IS 'Domovské letiště klubu (nejvýš jedno).';


--
-- Name: COLUMN lov_letiste.zem_sirka; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.lov_letiste.zem_sirka IS 'Zeměpisná šířka ve stupních (WGS 84), sever kladně.';


--
-- Name: COLUMN lov_letiste.zem_delka; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.lov_letiste.zem_delka IS 'Zeměpisná délka ve stupních (WGS 84), východ kladně.';


--
-- Name: COLUMN lov_letiste.nadm_vyska_ft; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.lov_letiste.nadm_vyska_ft IS 'Nadmořská výška ve stopách (jako v AIP).';


--
-- Name: COLUMN lov_letiste.rychla_volba; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.lov_letiste.rychla_volba IS 'Nabízí se v rychlé volbě místa; ostatní letiště jen přes Hledat… (mění správce v databázi).';


--
-- Name: lov_letiste_id_seq; Type: SEQUENCE; Schema: lkkl; Owner: -
--

ALTER TABLE lkkl.lov_letiste ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME lkkl.lov_letiste_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: lov_opravneni; Type: TABLE; Schema: lkkl; Owner: -
--

CREATE TABLE lkkl.lov_opravneni (
    id bigint NOT NULL,
    kod lkkl.kod NOT NULL,
    nazev lkkl.nazev NOT NULL,
    poradi lkkl.poradi NOT NULL,
    platny lkkl.platny NOT NULL
);


--
-- Name: TABLE lov_opravneni; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON TABLE lkkl.lov_opravneni IS 'Druh oprávnění osoby (FI(S), FE(S), FI(A), vlekař…) – určuje, koho nabídnout v posádce.';


--
-- Name: lov_opravneni_id_seq; Type: SEQUENCE; Schema: lkkl; Owner: -
--

ALTER TABLE lkkl.lov_opravneni ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME lkkl.lov_opravneni_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: lov_opravneni_kategorie; Type: TABLE; Schema: lkkl; Owner: -
--

CREATE TABLE lkkl.lov_opravneni_kategorie (
    opravneni_id bigint NOT NULL,
    kategorie_id bigint NOT NULL
);


--
-- Name: TABLE lov_opravneni_kategorie; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON TABLE lkkl.lov_opravneni_kategorie IS 'Pro které kategorie letadel se oprávnění smí vydat; bez řádku pro žádnou.';


--
-- Name: lov_opravneni_role; Type: TABLE; Schema: lkkl; Owner: -
--

CREATE TABLE lkkl.lov_opravneni_role (
    opravneni_id bigint NOT NULL,
    role_id bigint NOT NULL
);


--
-- Name: TABLE lov_opravneni_role; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON TABLE lkkl.lov_opravneni_role IS 'K jakým rolím v letu oprávnění opravňuje – nabídka osob v posádce.';


--
-- Name: lov_osnova; Type: TABLE; Schema: lkkl; Owner: -
--

CREATE TABLE lkkl.lov_osnova (
    id bigint NOT NULL,
    kod lkkl.kod NOT NULL,
    nazev lkkl.nazev NOT NULL,
    poradi lkkl.poradi NOT NULL,
    platny lkkl.platny NOT NULL,
    kategorie_id bigint NOT NULL
);


--
-- Name: TABLE lov_osnova; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON TABLE lkkl.lov_osnova IS 'Osnova (skupina úloh), např. Základní výcvik; obecné úlohy jako osnova Obecné.';


--
-- Name: COLUMN lov_osnova.kod; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.lov_osnova.kod IS 'Oficiální označení osnovy (IU, IA, II…) – zobrazuje se.';


--
-- Name: COLUMN lov_osnova.kategorie_id; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.lov_osnova.kategorie_id IS 'Kategorie letadla, pro kterou osnova platí; prázdné = pro všechny.';


--
-- Name: lov_osnova_id_seq; Type: SEQUENCE; Schema: lkkl; Owner: -
--

ALTER TABLE lkkl.lov_osnova ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME lkkl.lov_osnova_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: lov_osoba; Type: TABLE; Schema: lkkl; Owner: -
--

CREATE TABLE lkkl.lov_osoba (
    id bigint NOT NULL,
    jmeno text NOT NULL,
    prijmeni text NOT NULL,
    email text,
    telefon text,
    cislo_clena text,
    clen boolean DEFAULT true NOT NULL,
    platny lkkl.platny CONSTRAINT lov_osoba_aktivni_not_null NOT NULL,
    CONSTRAINT cislo_jen_u_clena CHECK (((cislo_clena IS NULL) OR clen)),
    CONSTRAINT lov_osoba_cislo_clena_check CHECK ((cislo_clena ~ '^[0-9]+$'::text)),
    CONSTRAINT lov_osoba_email_check CHECK ((email ~ '^[^@\s]+@[^@\s]+\.[^@\s]+$'::text)),
    CONSTRAINT lov_osoba_jmeno_check CHECK ((btrim(jmeno) <> ''::text)),
    CONSTRAINT lov_osoba_prijmeni_check CHECK ((btrim(prijmeni) <> ''::text)),
    CONSTRAINT lov_osoba_telefon_check CHECK ((telefon ~ '^\+[1-9][0-9]{7,14}$'::text))
);


--
-- Name: TABLE lov_osoba; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON TABLE lkkl.lov_osoba IS 'Osoby: členové klubu i externí (piloti a instruktoři z jiných klubů). Hosté se neevidují, u letu jen počtem.';


--
-- Name: COLUMN lov_osoba.email; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.lov_osoba.email IS 'Přihlášení a upozornění; jedinečný bez ohledu na velikost písmen.';


--
-- Name: COLUMN lov_osoba.telefon; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.lov_osoba.telefon IS 'Mezinárodní tvar bez mezer, např. +420601234567.';


--
-- Name: COLUMN lov_osoba.cislo_clena; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.lov_osoba.cislo_clena IS 'Číslo člena klubu (text kvůli úvodním nulám); jen u členů.';


--
-- Name: COLUMN lov_osoba.clen; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.lov_osoba.clen IS 'Člen klubu (ne = externí osoba).';


--
-- Name: COLUMN lov_osoba.platny; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.lov_osoba.platny IS 'Ne = bývalý člen nebo už nelétá: nenabízí se, nesmí se přihlásit, nejde nově použít; zůstává kvůli historii letů. V aplikaci „aktivní“.';


--
-- Name: lov_osoba_id_seq; Type: SEQUENCE; Schema: lkkl; Owner: -
--

ALTER TABLE lkkl.lov_osoba ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME lkkl.lov_osoba_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: lov_osoba_opravneni; Type: TABLE; Schema: lkkl; Owner: -
--

CREATE TABLE lkkl.lov_osoba_opravneni (
    osoba_id bigint NOT NULL,
    opravneni_id bigint NOT NULL,
    omezene boolean DEFAULT false NOT NULL
);


--
-- Name: TABLE lov_osoba_opravneni; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON TABLE lkkl.lov_osoba_opravneni IS 'Kdo má jaké oprávnění (zadává správce přímo v databázi).';


--
-- Name: COLUMN lov_osoba_opravneni.omezene; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.lov_osoba_opravneni.omezene IS 'Instruktor s omezením (vyučuje pod dohledem, nesmí povolit první sólo) – jen evidence, nabídku neovlivní.';


--
-- Name: lov_osoba_opravneni_kategorie; Type: TABLE; Schema: lkkl; Owner: -
--

CREATE TABLE lkkl.lov_osoba_opravneni_kategorie (
    osoba_id bigint NOT NULL,
    opravneni_id bigint NOT NULL,
    kategorie_id bigint NOT NULL
);


--
-- Name: TABLE lov_osoba_opravneni_kategorie; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON TABLE lkkl.lov_osoba_opravneni_kategorie IS 'Pro které kategorie letadel osoba oprávnění má (jen z povolených u oprávnění).';


--
-- Name: lov_prezkouseni; Type: TABLE; Schema: lkkl; Owner: -
--

CREATE TABLE lkkl.lov_prezkouseni (
    id bigint NOT NULL,
    kod lkkl.kod NOT NULL,
    nazev lkkl.nazev NOT NULL,
    poradi lkkl.poradi NOT NULL,
    platny lkkl.platny NOT NULL,
    kategorie_id bigint NOT NULL
);


--
-- Name: TABLE lov_prezkouseni; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON TABLE lkkl.lov_prezkouseni IS 'Typ přezkoušení (zkouška dovednosti, přezkoušení odborné způsobilosti, ověření instruktora) – u letu s účelem Přezkoušení místo úlohy.';


--
-- Name: COLUMN lov_prezkouseni.kod; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.lov_prezkouseni.kod IS 'Označení typu (ST-SPL, PC-SEP…) – zobrazuje se (štítek pásku).';


--
-- Name: COLUMN lov_prezkouseni.kategorie_id; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.lov_prezkouseni.kategorie_id IS 'Kategorie letadla, na které se přezkoušení létá.';


--
-- Name: lov_prezkouseni_id_seq; Type: SEQUENCE; Schema: lkkl; Owner: -
--

ALTER TABLE lkkl.lov_prezkouseni ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME lkkl.lov_prezkouseni_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: lov_prezkouseni_opravneni; Type: TABLE; Schema: lkkl; Owner: -
--

CREATE TABLE lkkl.lov_prezkouseni_opravneni (
    prezkouseni_id bigint NOT NULL,
    opravneni_id bigint NOT NULL
);


--
-- Name: TABLE lov_prezkouseni_opravneni; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON TABLE lkkl.lov_prezkouseni_opravneni IS 'Kdo smí přezkoušení provést (examinátor = PIC): oprávnění; nabídka examinátora v průvodci.';


--
-- Name: lov_role; Type: TABLE; Schema: lkkl; Owner: -
--

CREATE TABLE lkkl.lov_role (
    id bigint NOT NULL,
    kod lkkl.kod NOT NULL,
    nazev lkkl.nazev NOT NULL,
    poradi lkkl.poradi NOT NULL,
    platny lkkl.platny NOT NULL,
    ucel_id bigint,
    funkce_id bigint NOT NULL
);


--
-- Name: TABLE lov_role; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON TABLE lkkl.lov_role IS 'Role v letu, do které se nabízejí osoby podle oprávnění: kde v letu sedí (účel + funkce). Kódy používá program.';


--
-- Name: COLUMN lov_role.ucel_id; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.lov_role.ucel_id IS 'Účel letu; prázdný = vlečný let (jako let.ucel_id).';


--
-- Name: lov_role_id_seq; Type: SEQUENCE; Schema: lkkl; Owner: -
--

ALTER TABLE lkkl.lov_role ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME lkkl.lov_role_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: lov_typ; Type: TABLE; Schema: lkkl; Owner: -
--

CREATE TABLE lkkl.lov_typ (
    id bigint NOT NULL,
    nazev lkkl.nazev NOT NULL,
    kategorie_id bigint NOT NULL,
    pocet_mist smallint,
    kod lkkl.kod NOT NULL,
    poradi lkkl.poradi NOT NULL,
    platny lkkl.platny NOT NULL,
    CONSTRAINT lov_typ_pocet_mist_check CHECK ((pocet_mist > 0))
);


--
-- Name: TABLE lov_typ; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON TABLE lkkl.lov_typ IS 'Typy letadel; typ určuje kategorii.';


--
-- Name: COLUMN lov_typ.pocet_mist; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.lov_typ.pocet_mist IS 'Počet míst včetně pilota; prázdné = nezadáno.';


--
-- Name: lov_typ_id_seq; Type: SEQUENCE; Schema: lkkl; Owner: -
--

ALTER TABLE lkkl.lov_typ ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME lkkl.lov_typ_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: lov_ucel; Type: TABLE; Schema: lkkl; Owner: -
--

CREATE TABLE lkkl.lov_ucel (
    id bigint NOT NULL,
    kod lkkl.kod NOT NULL,
    nazev lkkl.nazev NOT NULL,
    poradi lkkl.poradi NOT NULL,
    platny lkkl.platny NOT NULL,
    uloha_povinna boolean DEFAULT false NOT NULL
);


--
-- Name: TABLE lov_ucel; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON TABLE lkkl.lov_ucel IS 'Účel letu. Vlek není účel – odvodí se z vazby kluzák–vlečná.';


--
-- Name: COLUMN lov_ucel.uloha_povinna; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.lov_ucel.uloha_povinna IS 'Let s tímto účelem musí mít úlohu.';


--
-- Name: lov_ucel_funkce; Type: TABLE; Schema: lkkl; Owner: -
--

CREATE TABLE lkkl.lov_ucel_funkce (
    ucel_id bigint NOT NULL,
    funkce_id bigint NOT NULL
);


--
-- Name: TABLE lov_ucel_funkce; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON TABLE lkkl.lov_ucel_funkce IS 'Povinné funkce účelu kromě PIC (výcvik → žák, sólo → dozor, přezkoušení → přezkoušený).';


--
-- Name: lov_ucel_id_seq; Type: SEQUENCE; Schema: lkkl; Owner: -
--

ALTER TABLE lkkl.lov_ucel ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME lkkl.lov_ucel_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: lov_uloha; Type: TABLE; Schema: lkkl; Owner: -
--

CREATE TABLE lkkl.lov_uloha (
    id bigint NOT NULL,
    kod lkkl.kod NOT NULL,
    nazev lkkl.nazev NOT NULL,
    poradi lkkl.poradi NOT NULL,
    platny lkkl.platny NOT NULL,
    osnova_id bigint NOT NULL
);


--
-- Name: TABLE lov_uloha; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON TABLE lkkl.lov_uloha IS 'Úloha osnovy; označení (např. B3) je součástí názvu.';


--
-- Name: COLUMN lov_uloha.kod; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.lov_uloha.kod IS 'Označení úlohy v osnově (4, 8P…) – zobrazuje se jako IU/8P.';


--
-- Name: lov_uloha_id_seq; Type: SEQUENCE; Schema: lkkl; Owner: -
--

ALTER TABLE lkkl.lov_uloha ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME lkkl.lov_uloha_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: lov_uloha_ucel; Type: TABLE; Schema: lkkl; Owner: -
--

CREATE TABLE lkkl.lov_uloha_ucel (
    uloha_id bigint NOT NULL,
    ucel_id bigint NOT NULL
);


--
-- Name: TABLE lov_uloha_ucel; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON TABLE lkkl.lov_uloha_ucel IS 'U kterých účelů letu se úloha nabízí (výcvik, sólo, normální, přezkoušení).';


--
-- Name: lov_zpusob_vzletu; Type: TABLE; Schema: lkkl; Owner: -
--

CREATE TABLE lkkl.lov_zpusob_vzletu (
    id bigint NOT NULL,
    kod lkkl.kod NOT NULL,
    nazev lkkl.nazev NOT NULL,
    poradi lkkl.poradi NOT NULL,
    platny lkkl.platny NOT NULL
);


--
-- Name: TABLE lov_zpusob_vzletu; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON TABLE lkkl.lov_zpusob_vzletu IS 'Způsob vzletu.';


--
-- Name: lov_zpusob_vzletu_id_seq; Type: SEQUENCE; Schema: lkkl; Owner: -
--

ALTER TABLE lkkl.lov_zpusob_vzletu ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME lkkl.lov_zpusob_vzletu_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: migrace; Type: TABLE; Schema: lkkl; Owner: -
--

CREATE TABLE lkkl.migrace (
    skript text NOT NULL,
    kdy timestamp with time zone DEFAULT now() NOT NULL,
    otisk text NOT NULL
);


--
-- Name: nastaveni; Type: TABLE; Schema: lkkl; Owner: -
--

CREATE TABLE lkkl.nastaveni (
    jediny boolean DEFAULT true NOT NULL,
    testovaci_provoz boolean DEFAULT true NOT NULL,
    CONSTRAINT nastaveni_jediny_check CHECK (jediny)
);


--
-- Name: TABLE nastaveni; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON TABLE lkkl.nastaveni IS 'Nastavení systému (jediný řádek, sloupec = jedno nastavení; nové přidá migrace).';


--
-- Name: COLUMN nastaveni.testovaci_provoz; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.nastaveni.testovaci_provoz IS 'Ano = aplikace ukazuje žlutý pruh TESTOVACÍ PROVOZ. Nic jiného neřídí.';


--
-- Name: posadka; Type: TABLE; Schema: lkkl; Owner: -
--

CREATE TABLE lkkl.posadka (
    let_id bigint NOT NULL,
    osoba_id bigint NOT NULL,
    funkce_id bigint NOT NULL
);


--
-- Name: TABLE posadka; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON TABLE lkkl.posadka IS 'Jmenovitě uvedené osoby letu; každá funkce nejvýš jednou, osoba nejvýš jednou.';


--
-- Name: relace; Type: TABLE; Schema: lkkl; Owner: -
--

CREATE TABLE lkkl.relace (
    id text NOT NULL,
    osoba_id bigint NOT NULL,
    puvodni_osoba_id bigint,
    vytvorena timestamp with time zone DEFAULT now() NOT NULL,
    posledni_aktivita timestamp with time zone DEFAULT now() NOT NULL,
    plati_do timestamp with time zone NOT NULL,
    zarizeni text,
    jen_cteni boolean DEFAULT false NOT NULL,
    CONSTRAINT jako_nekdo_jiny CHECK ((puvodni_osoba_id <> osoba_id)),
    CONSTRAINT plati_po_vytvoreni CHECK ((plati_do > vytvorena)),
    CONSTRAINT relace_id_check CHECK ((id ~ '^[0-9a-f]{64}$'::text))
);


--
-- Name: TABLE relace; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON TABLE lkkl.relace IS 'Přihlášená zařízení. Platí 30 dní od poslední aktivity.';


--
-- Name: COLUMN relace.id; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.relace.id IS 'SHA-256 (hex) náhodného klíče z cookie; samotný klíč se neukládá.';


--
-- Name: COLUMN relace.osoba_id; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.relace.osoba_id IS 'Za koho relace jedná.';


--
-- Name: COLUMN relace.puvodni_osoba_id; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.relace.puvodni_osoba_id IS 'Admin, který se přihlásil jako jiná osoba („přihlásit se jako“); jinak prázdné.';


--
-- Name: COLUMN relace.zarizeni; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.relace.zarizeni IS 'Popis zařízení (prohlížeč, systém) pro přehled přihlášení.';


--
-- Name: COLUMN relace.jen_cteni; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.relace.jen_cteni IS 'Přihlášeno jen ke čtení (sdílený počítač): server odmítne zápisy, práva se neuplatní.';


--
-- Name: relace_provoz; Type: TABLE; Schema: lkkl; Owner: -
--

CREATE TABLE lkkl.relace_provoz (
    relace_id text NOT NULL,
    den date NOT NULL,
    letiste_id bigint
);


--
-- Name: TABLE relace_provoz; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON TABLE lkkl.relace_provoz IS 'Můj provoz: nastavení relace na jeden den (letiště, osoby v relace_provoz_osoba).';


--
-- Name: COLUMN relace_provoz.den; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.relace_provoz.den IS 'Den (UTC), pro který nastavení platí; jiný den se nebere v úvahu.';


--
-- Name: COLUMN relace_provoz.letiste_id; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.relace_provoz.letiste_id IS 'Letiště, kde dnes létám; prázdné = domovské.';


--
-- Name: relace_provoz_osoba; Type: TABLE; Schema: lkkl; Owner: -
--

CREATE TABLE lkkl.relace_provoz_osoba (
    relace_id text NOT NULL,
    osoba_id bigint NOT NULL
);


--
-- Name: TABLE relace_provoz_osoba; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON TABLE lkkl.relace_provoz_osoba IS 'Osoby v provozu (filtr nabídky osob v posádce); žádný řádek = bez filtru.';


--
-- Name: ucet; Type: TABLE; Schema: lkkl; Owner: -
--

CREATE TABLE lkkl.ucet (
    osoba_id bigint NOT NULL,
    heslo_hash text,
    prihlaseni_povoleno boolean DEFAULT true CONSTRAINT ucet_aktivni_not_null NOT NULL,
    admin boolean DEFAULT false NOT NULL,
    zalozen timestamp with time zone DEFAULT now() NOT NULL,
    pozvanka_odeslana timestamp with time zone,
    heslo_zmeneno timestamp with time zone,
    posledni_prihlaseni timestamp with time zone,
    neuspesne_pokusy smallint DEFAULT 0 NOT NULL,
    zablokovano_do timestamp with time zone,
    smi_odblokovat boolean DEFAULT false NOT NULL,
    spravuje_osoby boolean DEFAULT false NOT NULL,
    spravuje_letadla boolean DEFAULT false NOT NULL,
    spravuje_vycvik boolean DEFAULT false NOT NULL,
    CONSTRAINT ucet_neuspesne_pokusy_check CHECK ((neuspesne_pokusy >= 0))
);


--
-- Name: TABLE ucet; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON TABLE lkkl.ucet IS 'Přihlašovací účet osoby; existence účtu = osoba aktivovaná v aplikaci.';


--
-- Name: COLUMN ucet.heslo_hash; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.ucet.heslo_hash IS 'Otisk hesla (argon2id, počítá aplikace); prázdné = heslo ještě nenastavené.';


--
-- Name: COLUMN ucet.prihlaseni_povoleno; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.ucet.prihlaseni_povoleno IS 'Ano = smí se přihlásit (přístup do aplikace); ne = přístup vypnutý bez ztráty historie. Přihlásit se jde jen s platnou (aktivní) osobou – v_ucet.smi_se_prihlasit.';


--
-- Name: COLUMN ucet.admin; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.ucet.admin IS 'Výjimečné právo: smí všechno.';


--
-- Name: COLUMN ucet.heslo_zmeneno; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.ucet.heslo_zmeneno IS 'Po změně hesla přestanou platit dříve vydané odkazy pro nastavení hesla.';


--
-- Name: COLUMN ucet.neuspesne_pokusy; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.ucet.neuspesne_pokusy IS 'Neúspěšná přihlášení od posledního úspěšného (ochrana proti hádání hesla).';


--
-- Name: COLUMN ucet.zablokovano_do; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.ucet.zablokovano_do IS 'Dočasné zablokování po příliš mnoha neúspěšných pokusech.';


--
-- Name: COLUMN ucet.smi_odblokovat; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.ucet.smi_odblokovat IS 'Výjimečné právo: smí odblokovat účet zablokovaný po neúspěšných pokusech.';


--
-- Name: COLUMN ucet.spravuje_osoby; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.ucet.spravuje_osoby IS 'Smí spravovat osoby (údaje, oprávnění, účty); admin smí vždy.';


--
-- Name: COLUMN ucet.spravuje_letadla; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.ucet.spravuje_letadla IS 'Smí spravovat letadla (mimo provoz); admin smí vždy.';


--
-- Name: COLUMN ucet.spravuje_vycvik; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.ucet.spravuje_vycvik IS 'Smí spravovat osnovy, úlohy a typy přezkoušení (editor výcviku na desktopu); admin vždy.';


--
-- Name: v_audit; Type: VIEW; Schema: lkkl; Owner: -
--

CREATE VIEW lkkl.v_audit AS
 SELECT au.id,
    au.kdy,
    au.transakce,
    au.tabulka,
    au.klic,
    au.let_id,
    au.operace,
        CASE
            WHEN (au.zdroj = 'databaze'::text) THEN 'přímo v databázi'::text
            WHEN (o.id IS NULL) THEN 'aplikace'::text
            WHEN (p.id IS NOT NULL) THEN (((((((p.jmeno || ' '::text) || p.prijmeni) || ' (jako '::text) || o.jmeno) || ' '::text) || o.prijmeni) || ')'::text)
            ELSE ((o.jmeno || ' '::text) || o.prijmeni)
        END AS kdo,
    lkkl.audit_akce(au.tabulka, au.operace, au.zmeny) AS akce,
    lkkl.audit_popis(au.tabulka, au.operace, au.zmeny) AS popis
   FROM ((lkkl.audit au
     LEFT JOIN lkkl.lov_osoba o ON ((o.id = au.osoba_id)))
     LEFT JOIN lkkl.lov_osoba p ON ((p.id = au.puvodni_osoba_id)));


--
-- Name: VIEW v_audit; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON VIEW lkkl.v_audit IS 'Auditní log čitelně: kdo, akce (odvozená ze změny), popis „popisek z → na“.';


--
-- Name: v_historie_letu; Type: VIEW; Schema: lkkl; Owner: -
--

CREATE VIEW lkkl.v_historie_letu AS
 SELECT let_id,
    transakce,
    min(kdy) AS kdy,
    min(kdo) AS kdo,
    (array_agg(akce ORDER BY
        CASE tabulka
            WHEN 'let'::text THEN 1
            WHEN 'posadka'::text THEN 2
            ELSE 3
        END, id))[1] AS akce,
    string_agg(popis, ', '::text ORDER BY
        CASE tabulka
            WHEN 'let'::text THEN 1
            WHEN 'posadka'::text THEN 2
            ELSE 3
        END, id) FILTER (WHERE (popis IS NOT NULL)) AS popis
   FROM lkkl.v_audit
  WHERE (let_id IS NOT NULL)
  GROUP BY let_id, transakce;


--
-- Name: VIEW v_historie_letu; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON VIEW lkkl.v_historie_letu IS 'Historie letu pro detail: jedna akce = jeden řádek (seřadit podle kdy).';


--
-- Name: v_let; Type: VIEW; Schema: lkkl; Owner: -
--

CREATE VIEW lkkl.v_let AS
 SELECT l.id,
        CASE
            WHEN (l.zruseni_duvod_id IS NOT NULL) THEN 'ZRUSEN'::text
            WHEN (l.cas_vzletu IS NULL) THEN 'NAPLANOVAN'::text
            WHEN (l.cas_pristani IS NULL) THEN 'VE_VZDUCHU'::text
            ELSE 'UKONCEN'::text
        END AS stav,
    ((COALESCE(l.cas_vzletu, l.zalozeno) AT TIME ZONE 'UTC'::text))::date AS den,
    l.letadlo_id,
    a.rejstrik,
    t.nazev AS typ,
    k.nazev AS kategorie,
    k.kod AS kategorie_kod,
    a.soukrome,
    l.ucel_id,
    u.nazev AS ucel,
    u.kod AS ucel_kod,
    (v.id IS NOT NULL) AS je_vlecny,
    v.id AS vleceny_let_id,
    l.vlecny_let_id,
    z.nazev AS zpusob_vzletu,
    z.kod AS zpusob_vzletu_kod,
    COALESCE((lv.kod)::text, l.misto_vzletu_popis) AS misto_vzletu,
    COALESCE((lp.kod)::text, l.misto_pristani_popis) AS misto_pristani,
    l.cas_vzletu,
    l.cas_pristani,
    l.doba_min,
        CASE
            WHEN (l.zruseni_duvod_id IS NOT NULL) THEN 0
            ELSE l.doba_min
        END AS doba_uctovana_min,
    l.pocet_pristani,
    (COALESCE((l.pob)::bigint, ( SELECT count(*) AS count
           FROM (lkkl.posadka p
             JOIN lkkl.lov_funkce f ON ((f.id = p.funkce_id)))
          WHERE ((p.let_id = l.id) AND f.na_palube))))::smallint AS pob,
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
    ((l.cas_pristani IS NOT NULL) AND (l.zalozeno > l.cas_pristani)) AS dodatecne,
    l.zalozil_id,
    l.zalozeno,
    l.verze,
    l.uloha_id,
    ((((((ulo.kod)::text || '/'::text) || (ul.kod)::text) || ' '::text) || (ul.nazev)::text))::lkkl.nazev AS uloha,
        CASE
            WHEN (((k.kod)::text = 'KLUZAK'::text) OR (v.id IS NOT NULL)) THEN 'PLACHTARSKY'::text
            ELSE 'MOTOROVY'::text
        END AS druh_provozu,
    ((l.cas_vzletu IS NOT NULL) AND (l.cas_pristani IS NULL) AND (l.zruseni_duvod_id IS NULL) AND (a.max_doba_min IS NOT NULL) AND ((now() - l.cas_vzletu) > ((a.max_doba_min)::double precision * '00:01:00'::interval))) AS prekrocena_doba,
    (((ulo.kod)::text || '/'::text) || (ul.kod)::text) AS uloha_oznaceni,
    l.prezkouseni_id,
    (((pr.kod)::text || ' '::text) || (pr.nazev)::text) AS prezkouseni,
    (pr.kod)::text AS prezkouseni_kod,
    l.vzlet_namereno
   FROM (((((((((((((((lkkl.let l
     JOIN lkkl.lov_letadlo a ON ((a.id = l.letadlo_id)))
     JOIN lkkl.lov_typ t ON ((t.id = a.typ_id)))
     JOIN lkkl.lov_kategorie k ON ((k.id = t.kategorie_id)))
     JOIN lkkl.lov_zpusob_vzletu z ON ((z.id = l.zpusob_vzletu_id)))
     LEFT JOIN lkkl.lov_ucel u ON ((u.id = l.ucel_id)))
     LEFT JOIN lkkl.let v ON ((v.vlecny_let_id = l.id)))
     LEFT JOIN lkkl.lov_letiste lv ON ((lv.id = l.misto_vzletu_id)))
     LEFT JOIN lkkl.lov_letiste lp ON ((lp.id = l.misto_pristani_id)))
     LEFT JOIN lkkl.posadka pic ON (((pic.let_id = l.id) AND (pic.funkce_id = ( SELECT lov_funkce.id
           FROM lkkl.lov_funkce
          WHERE ((lov_funkce.kod)::text = 'PIC'::text))))))
     LEFT JOIN lkkl.lov_osoba po ON ((po.id = pic.osoba_id)))
     LEFT JOIN lkkl.lov_osoba pl ON ((pl.id = l.platce_id)))
     LEFT JOIN lkkl.lov_duvod_zruseni dz ON ((dz.id = l.zruseni_duvod_id)))
     LEFT JOIN lkkl.lov_uloha ul ON ((ul.id = l.uloha_id)))
     LEFT JOIN lkkl.lov_osnova ulo ON ((ulo.id = ul.osnova_id)))
     LEFT JOIN lkkl.lov_prezkouseni pr ON ((pr.id = l.prezkouseni_id)));


--
-- Name: VIEW v_let; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON VIEW lkkl.v_let IS 'Lety s odvozeným stavem, dnem (UTC datum vzletu), vlekem, účtovanou dobou, příznakem „dodatečně“, druhem provozu (PLACHTARSKY = kluzák a vlečný let, MOTOROVY = ostatní) a příznakem překročené maximální doby letu (jen ve vzduchu, podle now()).';


--
-- Name: COLUMN v_let.vzlet_namereno; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON COLUMN lkkl.v_let.vzlet_namereno IS 'Naměřený vzlet na sekundy – jen pro stopky letu ve vzduchu.';


--
-- Name: v_lov_duvod_zruseni; Type: VIEW; Schema: lkkl; Owner: -
--

CREATE VIEW lkkl.v_lov_duvod_zruseni AS
 SELECT id,
    kod,
    nazev,
    poradi
   FROM lkkl.lov_duvod_zruseni
  WHERE platny
  ORDER BY poradi, nazev;


--
-- Name: VIEW v_lov_duvod_zruseni; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON VIEW lkkl.v_lov_duvod_zruseni IS 'Nabídka: platné důvody zrušení.';


--
-- Name: v_lov_funkce; Type: VIEW; Schema: lkkl; Owner: -
--

CREATE VIEW lkkl.v_lov_funkce AS
 SELECT id,
    kod,
    nazev,
    poradi,
    na_palube
   FROM lkkl.lov_funkce
  WHERE platny
  ORDER BY poradi, nazev;


--
-- Name: VIEW v_lov_funkce; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON VIEW lkkl.v_lov_funkce IS 'Nabídka: platné funkce v posádce.';


--
-- Name: v_lov_kategorie; Type: VIEW; Schema: lkkl; Owner: -
--

CREATE VIEW lkkl.v_lov_kategorie AS
 SELECT id,
    kod,
    nazev,
    poradi
   FROM lkkl.lov_kategorie
  WHERE platny
  ORDER BY poradi, nazev;


--
-- Name: VIEW v_lov_kategorie; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON VIEW lkkl.v_lov_kategorie IS 'Nabídka: platné kategorie.';


--
-- Name: v_lov_letadlo; Type: VIEW; Schema: lkkl; Owner: -
--

CREATE VIEW lkkl.v_lov_letadlo AS
 SELECT l.id,
    l.rejstrik,
    t.nazev AS typ,
    k.nazev AS kategorie,
    k.kod AS kategorie_kod,
    t.pocet_mist,
    l.max_doba_min,
    l.vlecne,
    l.soukrome,
    l.mimo_provoz,
    COALESCE((p.kod)::text, p.misto_pristani_popis) AS poloha,
    p.misto_pristani_id AS poloha_letiste_id,
    p.misto_pristani_popis AS poloha_popis
   FROM (((lkkl.lov_letadlo l
     JOIN lkkl.lov_typ t ON ((t.id = l.typ_id)))
     JOIN lkkl.lov_kategorie k ON ((k.id = t.kategorie_id)))
     LEFT JOIN LATERAL ( SELECT x.misto_pristani_id,
            x.misto_pristani_popis,
            lp.kod
           FROM (lkkl.let x
             LEFT JOIN lkkl.lov_letiste lp ON ((lp.id = x.misto_pristani_id)))
          WHERE ((x.letadlo_id = l.id) AND (x.cas_pristani IS NOT NULL) AND (x.zruseni_duvod_id IS NULL))
          ORDER BY x.cas_pristani DESC
         LIMIT 1) p ON (true))
  WHERE l.platny
  ORDER BY k.poradi, t.poradi, t.nazev, l.rejstrik;


--
-- Name: VIEW v_lov_letadlo; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON VIEW lkkl.v_lov_letadlo IS 'Platná letadla pro nabídky a obrazovky: typ, kategorie, počet míst, poloha (poslední evidované přistání – kód nebo popis, a zvlášť id letiště / popis: výchozí místo vzletu nového letu); i mimo provoz (zobrazí se, nejdou vybrat). Vyřazená se neukazují.';


--
-- Name: v_lov_letiste; Type: VIEW; Schema: lkkl; Owner: -
--

CREATE VIEW lkkl.v_lov_letiste AS
 SELECT id,
    kod,
    nazev,
    poradi,
    domovske,
    zem_sirka,
    zem_delka,
    nadm_vyska_ft,
    rychla_volba
   FROM lkkl.lov_letiste
  WHERE platny
  ORDER BY domovske DESC, poradi, nazev;


--
-- Name: VIEW v_lov_letiste; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON VIEW lkkl.v_lov_letiste IS 'Nabídka: platná letiště, domovské první.';


--
-- Name: v_lov_opravneni; Type: VIEW; Schema: lkkl; Owner: -
--

CREATE VIEW lkkl.v_lov_opravneni AS
 SELECT id,
    kod,
    nazev,
    poradi,
    platny
   FROM lkkl.lov_opravneni
  WHERE platny
  ORDER BY poradi, nazev;


--
-- Name: v_lov_osnova; Type: VIEW; Schema: lkkl; Owner: -
--

CREATE VIEW lkkl.v_lov_osnova AS
 SELECT id,
    kod,
    nazev,
    poradi,
    kategorie_id,
    (((kod)::text || ' – '::text) || (nazev)::text) AS popis
   FROM lkkl.lov_osnova
  WHERE platny
  ORDER BY poradi, nazev;


--
-- Name: VIEW v_lov_osnova; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON VIEW lkkl.v_lov_osnova IS 'Nabídka: platné osnovy; popis = „IU – Výcvik SPL…“.';


--
-- Name: v_lov_prezkouseni; Type: VIEW; Schema: lkkl; Owner: -
--

CREATE VIEW lkkl.v_lov_prezkouseni AS
 SELECT id,
    kod,
    nazev,
    poradi,
    kategorie_id,
    (((kod)::text || ' '::text) || (nazev)::text) AS popis
   FROM lkkl.lov_prezkouseni
  WHERE platny
  ORDER BY poradi, nazev;


--
-- Name: VIEW v_lov_prezkouseni; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON VIEW lkkl.v_lov_prezkouseni IS 'Nabídka: platné typy přezkoušení; popis = „PC-SEP Přezkoušení…“.';


--
-- Name: v_lov_typ; Type: VIEW; Schema: lkkl; Owner: -
--

CREATE VIEW lkkl.v_lov_typ AS
 SELECT id,
    kod,
    nazev,
    poradi,
    kategorie_id,
    pocet_mist
   FROM lkkl.lov_typ
  WHERE platny
  ORDER BY poradi, nazev;


--
-- Name: VIEW v_lov_typ; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON VIEW lkkl.v_lov_typ IS 'Nabídka: platné typy letadel.';


--
-- Name: v_lov_ucel; Type: VIEW; Schema: lkkl; Owner: -
--

CREATE VIEW lkkl.v_lov_ucel AS
 SELECT id,
    kod,
    nazev,
    poradi
   FROM lkkl.lov_ucel
  WHERE platny
  ORDER BY poradi, nazev;


--
-- Name: VIEW v_lov_ucel; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON VIEW lkkl.v_lov_ucel IS 'Nabídka: platné účely letu.';


--
-- Name: v_lov_uloha; Type: VIEW; Schema: lkkl; Owner: -
--

CREATE VIEW lkkl.v_lov_uloha AS
 SELECT u.id,
    u.kod,
    u.nazev,
    u.poradi,
    u.osnova_id,
    (((o.kod)::text || '/'::text) || (u.kod)::text) AS oznaceni,
    (((((o.kod)::text || '/'::text) || (u.kod)::text) || ' '::text) || (u.nazev)::text) AS popis
   FROM (lkkl.lov_uloha u
     JOIN lkkl.lov_osnova o ON ((o.id = u.osnova_id)))
  WHERE u.platny
  ORDER BY u.poradi, u.nazev;


--
-- Name: VIEW v_lov_uloha; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON VIEW lkkl.v_lov_uloha IS 'Nabídka: platné úlohy; oznaceni = „IU/8P“, popis = „IU/8P Přezkoušení…“.';


--
-- Name: v_lov_zpusob_vzletu; Type: VIEW; Schema: lkkl; Owner: -
--

CREATE VIEW lkkl.v_lov_zpusob_vzletu AS
 SELECT id,
    kod,
    nazev,
    poradi
   FROM lkkl.lov_zpusob_vzletu
  WHERE platny
  ORDER BY poradi, nazev;


--
-- Name: VIEW v_lov_zpusob_vzletu; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON VIEW lkkl.v_lov_zpusob_vzletu IS 'Nabídka: platné způsoby vzletu.';


--
-- Name: v_osoba_opravneni; Type: VIEW; Schema: lkkl; Owner: -
--

CREATE VIEW lkkl.v_osoba_opravneni AS
SELECT
    NULL::bigint AS id,
    NULL::text AS prijmeni,
    NULL::text AS jmeno,
    NULL::lkkl.platny AS platny,
    NULL::text AS opravneni;


--
-- Name: VIEW v_osoba_opravneni; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON VIEW lkkl.v_osoba_opravneni IS 'Přehled oprávnění osob s kategoriemi a omezením (kontrola zadání); i neplatné osoby.';


--
-- Name: v_osoba_prezkouseni; Type: VIEW; Schema: lkkl; Owner: -
--

CREATE VIEW lkkl.v_osoba_prezkouseni AS
 SELECT DISTINCT oo.osoba_id,
    p.id AS prezkouseni_id
   FROM (((((lkkl.lov_osoba_opravneni oo
     JOIN lkkl.lov_opravneni o ON (((o.id = oo.opravneni_id) AND o.platny)))
     JOIN lkkl.lov_prezkouseni_opravneni po ON ((po.opravneni_id = oo.opravneni_id)))
     JOIN lkkl.lov_prezkouseni p ON (((p.id = po.prezkouseni_id) AND p.platny)))
     JOIN lkkl.lov_osoba_opravneni_kategorie ok ON (((ok.osoba_id = oo.osoba_id) AND (ok.opravneni_id = oo.opravneni_id) AND (ok.kategorie_id = p.kategorie_id))))
     JOIN lkkl.lov_kategorie k ON (((k.id = p.kategorie_id) AND k.platny)));


--
-- Name: VIEW v_osoba_prezkouseni; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON VIEW lkkl.v_osoba_prezkouseni IS 'Která přezkoušení osoba smí provést (oprávnění pro kategorii typu) – nabídka examinátora.';


--
-- Name: v_osoba_smi; Type: VIEW; Schema: lkkl; Owner: -
--

CREATE VIEW lkkl.v_osoba_smi AS
 SELECT DISTINCT oo.osoba_id,
    r.kod AS role_kod,
    u.kod AS ucel_kod,
    f.kod AS funkce_kod,
    k.kod AS kategorie_kod
   FROM (((((((lkkl.lov_osoba_opravneni oo
     JOIN lkkl.lov_opravneni o ON (((o.id = oo.opravneni_id) AND o.platny)))
     JOIN lkkl.lov_osoba_opravneni_kategorie ok ON (((ok.osoba_id = oo.osoba_id) AND (ok.opravneni_id = oo.opravneni_id))))
     JOIN lkkl.lov_kategorie k ON (((k.id = ok.kategorie_id) AND k.platny)))
     JOIN lkkl.lov_opravneni_role orl ON ((orl.opravneni_id = oo.opravneni_id)))
     JOIN lkkl.lov_role r ON (((r.id = orl.role_id) AND r.platny)))
     LEFT JOIN lkkl.lov_ucel u ON ((u.id = r.ucel_id)))
     JOIN lkkl.lov_funkce f ON (((f.id = r.funkce_id) AND f.platny)))
  WHERE ((r.ucel_id IS NULL) OR u.platny);


--
-- Name: VIEW v_osoba_smi; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON VIEW lkkl.v_osoba_smi IS 'Role, které osoba smí zastat: role, účel (prázdný = vlečný let), funkce a kategorie letadla – jen platné položky číselníků.';


--
-- Name: v_relace_letiste; Type: VIEW; Schema: lkkl; Owner: -
--

CREATE VIEW lkkl.v_relace_letiste AS
 SELECT r.id AS relace_id,
    l.id AS letiste_id,
    l.kod,
    l.nazev,
    l.zem_sirka,
    l.zem_delka,
    l.domovske
   FROM ((lkkl.relace r
     LEFT JOIN lkkl.relace_provoz rp ON (((rp.relace_id = r.id) AND (rp.den = ((now() AT TIME ZONE 'UTC'::text))::date))))
     JOIN lkkl.lov_letiste l ON ((l.id = COALESCE(rp.letiste_id, ( SELECT lov_letiste.id
           FROM lkkl.lov_letiste
          WHERE lov_letiste.domovske)))));


--
-- Name: VIEW v_relace_letiste; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON VIEW lkkl.v_relace_letiste IS 'Dnešní letiště relace: zvolené v mém provozu, jinak domovské.';


--
-- Name: v_relace_osoba; Type: VIEW; Schema: lkkl; Owner: -
--

CREATE VIEW lkkl.v_relace_osoba AS
 SELECT ro.relace_id,
    ro.osoba_id
   FROM (lkkl.relace_provoz_osoba ro
     JOIN lkkl.relace_provoz rp ON ((rp.relace_id = ro.relace_id)))
  WHERE (rp.den = ((now() AT TIME ZONE 'UTC'::text))::date);


--
-- Name: VIEW v_relace_osoba; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON VIEW lkkl.v_relace_osoba IS 'Dnešní osoby v provozu relace (filtr nabídky osob).';


--
-- Name: v_souhrn_dne; Type: VIEW; Schema: lkkl; Owner: -
--

CREATE VIEW lkkl.v_souhrn_dne AS
 SELECT den,
    druh_provozu,
    letadlo_id,
    rejstrik,
    je_vlecny,
    (count(*))::integer AS lety,
    (sum(pocet_pristani))::integer AS pristani,
    (sum(doba_uctovana_min))::integer AS minut,
    (count(*) FILTER (WHERE ((zpusob_vzletu_kod)::text = 'NAVIJAK'::text)))::integer AS navijaky
   FROM lkkl.v_let
  WHERE (stav = 'UKONCEN'::text)
  GROUP BY den, druh_provozu, letadlo_id, rejstrik, je_vlecny;


--
-- Name: VIEW v_souhrn_dne; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON VIEW lkkl.v_souhrn_dne IS 'Souhrn dne: ukončené lety po druhu provozu a letadle (vlečná ve vleku zvlášť, je_vlecny) – počet letů, přistání, účtovaných minut a startů navijákem. Den = UTC datum vzletu (jako v_let).';


--
-- Name: v_ucet; Type: VIEW; Schema: lkkl; Owner: -
--

CREATE VIEW lkkl.v_ucet AS
 SELECT u.osoba_id,
    o.jmeno,
    o.prijmeni,
    o.email,
    (u.heslo_hash IS NOT NULL) AS ma_heslo,
    (u.prihlaseni_povoleno AND o.platny) AS smi_se_prihlasit,
    u.admin,
    u.zalozen,
    u.pozvanka_odeslana,
    u.posledni_prihlaseni,
    u.zablokovano_do,
    u.smi_odblokovat,
    u.spravuje_osoby,
    u.spravuje_letadla,
    u.spravuje_vycvik
   FROM (lkkl.ucet u
     JOIN lkkl.lov_osoba o ON ((o.id = u.osoba_id)));


--
-- Name: VIEW v_ucet; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON VIEW lkkl.v_ucet IS 'Účty s údaji osoby (bez otisku hesla); smí se přihlásit = účet aktivní a osoba platná.';


--
-- Name: v_uloha_nabidka; Type: VIEW; Schema: lkkl; Owner: -
--

CREATE VIEW lkkl.v_uloha_nabidka AS
 SELECT u.id,
    u.nazev,
    u.poradi,
    o.id AS osnova_id,
    o.nazev AS osnova,
    o.poradi AS osnova_poradi,
    uu.ucel_id,
    o.kategorie_id,
    (((o.kod)::text || '/'::text) || (u.kod)::text) AS oznaceni,
    (((((o.kod)::text || '/'::text) || (u.kod)::text) || ' '::text) || (u.nazev)::text) AS popis,
    (((o.kod)::text || ' – '::text) || (o.nazev)::text) AS osnova_popis
   FROM ((lkkl.lov_uloha u
     JOIN lkkl.lov_osnova o ON ((o.id = u.osnova_id)))
     JOIN lkkl.lov_uloha_ucel uu ON ((uu.uloha_id = u.id)))
  WHERE (u.platny AND o.platny)
  ORDER BY o.poradi, o.nazev, u.poradi, u.nazev;


--
-- Name: VIEW v_uloha_nabidka; Type: COMMENT; Schema: lkkl; Owner: -
--

COMMENT ON VIEW lkkl.v_uloha_nabidka IS 'Úlohy pro průvodce: filtrovat podle ucel_id a kategorie_id (prázdná = všechny kategorie); oznaceni „IU/8P“, popis „IU/8P Přezkoušení…“, osnova_popis „IU – Výcvik SPL…“.';


--
-- Name: audit audit_pkey; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.audit
    ADD CONSTRAINT audit_pkey PRIMARY KEY (id);


--
-- Name: email email_pkey; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.email
    ADD CONSTRAINT email_pkey PRIMARY KEY (id);


--
-- Name: let let_pkey; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.let
    ADD CONSTRAINT let_pkey PRIMARY KEY (id);


--
-- Name: let_tg let_tg_pkey; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.let_tg
    ADD CONSTRAINT let_tg_pkey PRIMARY KEY (let_id, cas);


--
-- Name: let let_vlecny_let_id_key; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.let
    ADD CONSTRAINT let_vlecny_let_id_key UNIQUE (vlecny_let_id);


--
-- Name: let letadlo_bez_prekryvu; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.let
    ADD CONSTRAINT letadlo_bez_prekryvu EXCLUDE USING gist (letadlo_id WITH =, tstzrange(vzlet_namereno, pristani_namereno) WITH &&) WHERE (((vzlet_namereno IS NOT NULL) AND (zruseni_duvod_id IS NULL)));


--
-- Name: lov_audit_popisek lov_audit_popisek_pkey; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_audit_popisek
    ADD CONSTRAINT lov_audit_popisek_pkey PRIMARY KEY (tabulka, sloupec);


--
-- Name: lov_duvod_zruseni lov_duvod_zruseni_kod_key; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_duvod_zruseni
    ADD CONSTRAINT lov_duvod_zruseni_kod_key UNIQUE (kod);


--
-- Name: lov_duvod_zruseni lov_duvod_zruseni_pkey; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_duvod_zruseni
    ADD CONSTRAINT lov_duvod_zruseni_pkey PRIMARY KEY (id);


--
-- Name: lov_funkce lov_funkce_kod_key; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_funkce
    ADD CONSTRAINT lov_funkce_kod_key UNIQUE (kod);


--
-- Name: lov_funkce lov_funkce_pkey; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_funkce
    ADD CONSTRAINT lov_funkce_pkey PRIMARY KEY (id);


--
-- Name: lov_kategorie lov_kategorie_kod_key; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_kategorie
    ADD CONSTRAINT lov_kategorie_kod_key UNIQUE (kod);


--
-- Name: lov_kategorie lov_kategorie_pkey; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_kategorie
    ADD CONSTRAINT lov_kategorie_pkey PRIMARY KEY (id);


--
-- Name: lov_letadlo lov_letadlo_pkey; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_letadlo
    ADD CONSTRAINT lov_letadlo_pkey PRIMARY KEY (id);


--
-- Name: lov_letadlo lov_letadlo_rejstrik_key; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_letadlo
    ADD CONSTRAINT lov_letadlo_rejstrik_key UNIQUE (rejstrik);


--
-- Name: lov_letiste lov_letiste_kod_key; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_letiste
    ADD CONSTRAINT lov_letiste_kod_key UNIQUE (kod);


--
-- Name: lov_letiste lov_letiste_pkey; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_letiste
    ADD CONSTRAINT lov_letiste_pkey PRIMARY KEY (id);


--
-- Name: lov_opravneni_kategorie lov_opravneni_kategorie_pkey; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_opravneni_kategorie
    ADD CONSTRAINT lov_opravneni_kategorie_pkey PRIMARY KEY (opravneni_id, kategorie_id);


--
-- Name: lov_opravneni lov_opravneni_kod_key; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_opravneni
    ADD CONSTRAINT lov_opravneni_kod_key UNIQUE (kod);


--
-- Name: lov_opravneni lov_opravneni_pkey; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_opravneni
    ADD CONSTRAINT lov_opravneni_pkey PRIMARY KEY (id);


--
-- Name: lov_opravneni_role lov_opravneni_role_pkey; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_opravneni_role
    ADD CONSTRAINT lov_opravneni_role_pkey PRIMARY KEY (opravneni_id, role_id);


--
-- Name: lov_osnova lov_osnova_kod_key; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_osnova
    ADD CONSTRAINT lov_osnova_kod_key UNIQUE (kod);


--
-- Name: lov_osnova lov_osnova_pkey; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_osnova
    ADD CONSTRAINT lov_osnova_pkey PRIMARY KEY (id);


--
-- Name: lov_osoba lov_osoba_cislo_clena_key; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_osoba
    ADD CONSTRAINT lov_osoba_cislo_clena_key UNIQUE (cislo_clena);


--
-- Name: lov_osoba_opravneni_kategorie lov_osoba_opravneni_kategorie_pkey; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_osoba_opravneni_kategorie
    ADD CONSTRAINT lov_osoba_opravneni_kategorie_pkey PRIMARY KEY (osoba_id, opravneni_id, kategorie_id);


--
-- Name: lov_osoba_opravneni lov_osoba_opravneni_pkey; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_osoba_opravneni
    ADD CONSTRAINT lov_osoba_opravneni_pkey PRIMARY KEY (osoba_id, opravneni_id);


--
-- Name: lov_osoba lov_osoba_pkey; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_osoba
    ADD CONSTRAINT lov_osoba_pkey PRIMARY KEY (id);


--
-- Name: lov_prezkouseni lov_prezkouseni_kod_key; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_prezkouseni
    ADD CONSTRAINT lov_prezkouseni_kod_key UNIQUE (kod);


--
-- Name: lov_prezkouseni_opravneni lov_prezkouseni_opravneni_pkey; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_prezkouseni_opravneni
    ADD CONSTRAINT lov_prezkouseni_opravneni_pkey PRIMARY KEY (prezkouseni_id, opravneni_id);


--
-- Name: lov_prezkouseni lov_prezkouseni_pkey; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_prezkouseni
    ADD CONSTRAINT lov_prezkouseni_pkey PRIMARY KEY (id);


--
-- Name: lov_role lov_role_kod_key; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_role
    ADD CONSTRAINT lov_role_kod_key UNIQUE (kod);


--
-- Name: lov_role lov_role_pkey; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_role
    ADD CONSTRAINT lov_role_pkey PRIMARY KEY (id);


--
-- Name: lov_role lov_role_ucel_id_funkce_id_key; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_role
    ADD CONSTRAINT lov_role_ucel_id_funkce_id_key UNIQUE NULLS NOT DISTINCT (ucel_id, funkce_id);


--
-- Name: lov_typ lov_typ_kod_key; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_typ
    ADD CONSTRAINT lov_typ_kod_key UNIQUE (kod);


--
-- Name: lov_typ lov_typ_pkey; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_typ
    ADD CONSTRAINT lov_typ_pkey PRIMARY KEY (id);


--
-- Name: lov_ucel_funkce lov_ucel_funkce_pkey; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_ucel_funkce
    ADD CONSTRAINT lov_ucel_funkce_pkey PRIMARY KEY (ucel_id, funkce_id);


--
-- Name: lov_ucel lov_ucel_kod_key; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_ucel
    ADD CONSTRAINT lov_ucel_kod_key UNIQUE (kod);


--
-- Name: lov_ucel lov_ucel_pkey; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_ucel
    ADD CONSTRAINT lov_ucel_pkey PRIMARY KEY (id);


--
-- Name: lov_uloha lov_uloha_osnova_kod; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_uloha
    ADD CONSTRAINT lov_uloha_osnova_kod UNIQUE (osnova_id, kod);


--
-- Name: lov_uloha lov_uloha_pkey; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_uloha
    ADD CONSTRAINT lov_uloha_pkey PRIMARY KEY (id);


--
-- Name: lov_uloha_ucel lov_uloha_ucel_pkey; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_uloha_ucel
    ADD CONSTRAINT lov_uloha_ucel_pkey PRIMARY KEY (uloha_id, ucel_id);


--
-- Name: lov_zpusob_vzletu lov_zpusob_vzletu_kod_key; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_zpusob_vzletu
    ADD CONSTRAINT lov_zpusob_vzletu_kod_key UNIQUE (kod);


--
-- Name: lov_zpusob_vzletu lov_zpusob_vzletu_pkey; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_zpusob_vzletu
    ADD CONSTRAINT lov_zpusob_vzletu_pkey PRIMARY KEY (id);


--
-- Name: migrace migrace_pkey; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.migrace
    ADD CONSTRAINT migrace_pkey PRIMARY KEY (skript);


--
-- Name: nastaveni nastaveni_pkey; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.nastaveni
    ADD CONSTRAINT nastaveni_pkey PRIMARY KEY (jediny);


--
-- Name: posadka posadka_let_id_funkce_id_key; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.posadka
    ADD CONSTRAINT posadka_let_id_funkce_id_key UNIQUE (let_id, funkce_id);


--
-- Name: posadka posadka_pkey; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.posadka
    ADD CONSTRAINT posadka_pkey PRIMARY KEY (let_id, osoba_id);


--
-- Name: relace relace_pkey; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.relace
    ADD CONSTRAINT relace_pkey PRIMARY KEY (id);


--
-- Name: relace_provoz_osoba relace_provoz_osoba_pkey; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.relace_provoz_osoba
    ADD CONSTRAINT relace_provoz_osoba_pkey PRIMARY KEY (relace_id, osoba_id);


--
-- Name: relace_provoz relace_provoz_pkey; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.relace_provoz
    ADD CONSTRAINT relace_provoz_pkey PRIMARY KEY (relace_id);


--
-- Name: ucet ucet_pkey; Type: CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.ucet
    ADD CONSTRAINT ucet_pkey PRIMARY KEY (osoba_id);


--
-- Name: audit_let; Type: INDEX; Schema: lkkl; Owner: -
--

CREATE INDEX audit_let ON lkkl.audit USING btree (let_id) WHERE (let_id IS NOT NULL);


--
-- Name: audit_tabulka_kdy; Type: INDEX; Schema: lkkl; Owner: -
--

CREATE INDEX audit_tabulka_kdy ON lkkl.audit USING btree (tabulka, kdy);


--
-- Name: email_osoba; Type: INDEX; Schema: lkkl; Owner: -
--

CREATE INDEX email_osoba ON lkkl.email USING btree (osoba_id, kdy);


--
-- Name: let_cas_vzletu; Type: INDEX; Schema: lkkl; Owner: -
--

CREATE INDEX let_cas_vzletu ON lkkl.let USING btree (cas_vzletu);


--
-- Name: let_letadlo; Type: INDEX; Schema: lkkl; Owner: -
--

CREATE INDEX let_letadlo ON lkkl.let USING btree (letadlo_id);


--
-- Name: let_prezkouseni; Type: INDEX; Schema: lkkl; Owner: -
--

CREATE INDEX let_prezkouseni ON lkkl.let USING btree (prezkouseni_id) WHERE (prezkouseni_id IS NOT NULL);


--
-- Name: let_uloha; Type: INDEX; Schema: lkkl; Owner: -
--

CREATE INDEX let_uloha ON lkkl.let USING btree (uloha_id) WHERE (uloha_id IS NOT NULL);


--
-- Name: lov_letiste_jedno_domovske; Type: INDEX; Schema: lkkl; Owner: -
--

CREATE UNIQUE INDEX lov_letiste_jedno_domovske ON lkkl.lov_letiste USING btree (domovske) WHERE domovske;


--
-- Name: lov_opravneni_kategorie_kategorie; Type: INDEX; Schema: lkkl; Owner: -
--

CREATE INDEX lov_opravneni_kategorie_kategorie ON lkkl.lov_opravneni_kategorie USING btree (kategorie_id);


--
-- Name: lov_opravneni_role_role; Type: INDEX; Schema: lkkl; Owner: -
--

CREATE INDEX lov_opravneni_role_role ON lkkl.lov_opravneni_role USING btree (role_id);


--
-- Name: lov_osoba_email_jedinecny; Type: INDEX; Schema: lkkl; Owner: -
--

CREATE UNIQUE INDEX lov_osoba_email_jedinecny ON lkkl.lov_osoba USING btree (lower(email));


--
-- Name: lov_osoba_opravneni_kategorie_rozsah; Type: INDEX; Schema: lkkl; Owner: -
--

CREATE INDEX lov_osoba_opravneni_kategorie_rozsah ON lkkl.lov_osoba_opravneni_kategorie USING btree (opravneni_id, kategorie_id);


--
-- Name: lov_osoba_opravneni_opravneni; Type: INDEX; Schema: lkkl; Owner: -
--

CREATE INDEX lov_osoba_opravneni_opravneni ON lkkl.lov_osoba_opravneni USING btree (opravneni_id);


--
-- Name: lov_prezkouseni_kategorie; Type: INDEX; Schema: lkkl; Owner: -
--

CREATE INDEX lov_prezkouseni_kategorie ON lkkl.lov_prezkouseni USING btree (kategorie_id);


--
-- Name: lov_prezkouseni_opravneni_opravneni; Type: INDEX; Schema: lkkl; Owner: -
--

CREATE INDEX lov_prezkouseni_opravneni_opravneni ON lkkl.lov_prezkouseni_opravneni USING btree (opravneni_id);


--
-- Name: lov_role_funkce; Type: INDEX; Schema: lkkl; Owner: -
--

CREATE INDEX lov_role_funkce ON lkkl.lov_role USING btree (funkce_id);


--
-- Name: lov_uloha_osnova; Type: INDEX; Schema: lkkl; Owner: -
--

CREATE INDEX lov_uloha_osnova ON lkkl.lov_uloha USING btree (osnova_id);


--
-- Name: lov_uloha_ucel_ucel; Type: INDEX; Schema: lkkl; Owner: -
--

CREATE INDEX lov_uloha_ucel_ucel ON lkkl.lov_uloha_ucel USING btree (ucel_id);


--
-- Name: posadka_osoba; Type: INDEX; Schema: lkkl; Owner: -
--

CREATE INDEX posadka_osoba ON lkkl.posadka USING btree (osoba_id);


--
-- Name: relace_osoba; Type: INDEX; Schema: lkkl; Owner: -
--

CREATE INDEX relace_osoba ON lkkl.relace USING btree (osoba_id);


--
-- Name: relace_provoz_letiste; Type: INDEX; Schema: lkkl; Owner: -
--

CREATE INDEX relace_provoz_letiste ON lkkl.relace_provoz USING btree (letiste_id);


--
-- Name: relace_provoz_osoba_osoba; Type: INDEX; Schema: lkkl; Owner: -
--

CREATE INDEX relace_provoz_osoba_osoba ON lkkl.relace_provoz_osoba USING btree (osoba_id);


--
-- Name: v_osoba_opravneni _RETURN; Type: RULE; Schema: lkkl; Owner: -
--

CREATE OR REPLACE VIEW lkkl.v_osoba_opravneni AS
 SELECT os.id,
    os.prijmeni,
    os.jmeno,
    os.platny,
    string_agg((((((o.nazev)::text || ' ('::text) || COALESCE(ok.kategorie, '–'::text)) ||
        CASE
            WHEN oo.omezene THEN '; omezené'::text
            ELSE ''::text
        END) || ')'::text), ', '::text ORDER BY o.poradi) AS opravneni
   FROM (((lkkl.lov_osoba os
     LEFT JOIN lkkl.lov_osoba_opravneni oo ON ((oo.osoba_id = os.id)))
     LEFT JOIN lkkl.lov_opravneni o ON ((o.id = oo.opravneni_id)))
     LEFT JOIN LATERAL ( SELECT string_agg((k.nazev)::text, ', '::text ORDER BY k.poradi) AS kategorie
           FROM (lkkl.lov_osoba_opravneni_kategorie x
             JOIN lkkl.lov_kategorie k ON ((k.id = x.kategorie_id)))
          WHERE ((x.osoba_id = oo.osoba_id) AND (x.opravneni_id = oo.opravneni_id))) ok ON (true))
  GROUP BY os.id
  ORDER BY os.prijmeni, os.jmeno;


--
-- Name: let audit; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER audit AFTER INSERT OR DELETE OR UPDATE ON lkkl.let FOR EACH ROW EXECUTE FUNCTION lkkl.audit_zapsat('verze');


--
-- Name: let_tg audit; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER audit AFTER INSERT OR DELETE OR UPDATE ON lkkl.let_tg FOR EACH ROW EXECUTE FUNCTION lkkl.audit_zapsat();


--
-- Name: lov_letadlo audit; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER audit AFTER INSERT OR DELETE OR UPDATE ON lkkl.lov_letadlo FOR EACH ROW EXECUTE FUNCTION lkkl.audit_zapsat();


--
-- Name: lov_opravneni audit; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER audit AFTER INSERT OR DELETE OR UPDATE ON lkkl.lov_opravneni FOR EACH ROW EXECUTE FUNCTION lkkl.audit_zapsat('poradi');


--
-- Name: lov_opravneni_kategorie audit; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER audit AFTER INSERT OR DELETE OR UPDATE ON lkkl.lov_opravneni_kategorie FOR EACH ROW EXECUTE FUNCTION lkkl.audit_zapsat();


--
-- Name: lov_opravneni_role audit; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER audit AFTER INSERT OR DELETE OR UPDATE ON lkkl.lov_opravneni_role FOR EACH ROW EXECUTE FUNCTION lkkl.audit_zapsat();


--
-- Name: lov_osnova audit; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER audit AFTER INSERT OR DELETE OR UPDATE ON lkkl.lov_osnova FOR EACH ROW EXECUTE FUNCTION lkkl.audit_zapsat('poradi');


--
-- Name: lov_osoba audit; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER audit AFTER INSERT OR DELETE OR UPDATE ON lkkl.lov_osoba FOR EACH ROW EXECUTE FUNCTION lkkl.audit_zapsat();


--
-- Name: lov_osoba_opravneni audit; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER audit AFTER INSERT OR DELETE OR UPDATE ON lkkl.lov_osoba_opravneni FOR EACH ROW EXECUTE FUNCTION lkkl.audit_zapsat();


--
-- Name: lov_osoba_opravneni_kategorie audit; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER audit AFTER INSERT OR DELETE OR UPDATE ON lkkl.lov_osoba_opravneni_kategorie FOR EACH ROW EXECUTE FUNCTION lkkl.audit_zapsat();


--
-- Name: lov_prezkouseni audit; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER audit AFTER INSERT OR DELETE OR UPDATE ON lkkl.lov_prezkouseni FOR EACH ROW EXECUTE FUNCTION lkkl.audit_zapsat('poradi');


--
-- Name: lov_prezkouseni_opravneni audit; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER audit AFTER INSERT OR DELETE OR UPDATE ON lkkl.lov_prezkouseni_opravneni FOR EACH ROW EXECUTE FUNCTION lkkl.audit_zapsat();


--
-- Name: lov_uloha audit; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER audit AFTER INSERT OR DELETE OR UPDATE ON lkkl.lov_uloha FOR EACH ROW EXECUTE FUNCTION lkkl.audit_zapsat('poradi');


--
-- Name: lov_uloha_ucel audit; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER audit AFTER INSERT OR DELETE OR UPDATE ON lkkl.lov_uloha_ucel FOR EACH ROW EXECUTE FUNCTION lkkl.audit_zapsat();


--
-- Name: posadka audit; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER audit AFTER INSERT OR DELETE OR UPDATE ON lkkl.posadka FOR EACH ROW EXECUTE FUNCTION lkkl.audit_zapsat();


--
-- Name: ucet audit; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER audit AFTER INSERT OR DELETE OR UPDATE ON lkkl.ucet FOR EACH ROW EXECUTE FUNCTION lkkl.audit_zapsat('heslo_hash', 'posledni_prihlaseni', 'neuspesne_pokusy');


--
-- Name: audit audit_jen_doplnovat; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER audit_jen_doplnovat BEFORE DELETE OR UPDATE ON lkkl.audit FOR EACH ROW EXECUTE FUNCTION lkkl.audit_jen_doplnovat();


--
-- Name: audit audit_nevyprazdnovat; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER audit_nevyprazdnovat BEFORE TRUNCATE ON lkkl.audit FOR EACH STATEMENT EXECUTE FUNCTION lkkl.nevyprazdnovat();


--
-- Name: let let_cas_ne_v_budoucnosti; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER let_cas_ne_v_budoucnosti BEFORE INSERT OR UPDATE OF vzlet_namereno, pristani_namereno ON lkkl.let FOR EACH ROW EXECUTE FUNCTION lkkl.cas_ne_v_budoucnosti();


--
-- Name: let let_doplnit_misto; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER let_doplnit_misto BEFORE INSERT OR UPDATE ON lkkl.let FOR EACH ROW EXECUTE FUNCTION lkkl.let_doplnit_misto();


--
-- Name: let let_kontrola; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE CONSTRAINT TRIGGER let_kontrola AFTER INSERT OR UPDATE ON lkkl.let DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION lkkl.let_kontrola();


--
-- Name: let let_letadlo_volne; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER let_letadlo_volne BEFORE INSERT OR UPDATE OF letadlo_id, vzlet_namereno, pristani_namereno, zruseni_duvod_id ON lkkl.let FOR EACH ROW EXECUTE FUNCTION lkkl.let_letadlo_volne();


--
-- Name: let let_nemazat; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER let_nemazat BEFORE DELETE ON lkkl.let FOR EACH ROW EXECUTE FUNCTION lkkl.let_nemazat();


--
-- Name: let let_nevyprazdnovat; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER let_nevyprazdnovat BEFORE TRUNCATE ON lkkl.let FOR EACH STATEMENT EXECUTE FUNCTION lkkl.nevyprazdnovat();


--
-- Name: let_tg let_tg_cas_ne_v_budoucnosti; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER let_tg_cas_ne_v_budoucnosti BEFORE INSERT OR UPDATE OF cas ON lkkl.let_tg FOR EACH ROW EXECUTE FUNCTION lkkl.cas_ne_v_budoucnosti();


--
-- Name: let_tg let_tg_kontrola; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE CONSTRAINT TRIGGER let_tg_kontrola AFTER INSERT OR DELETE OR UPDATE ON lkkl.let_tg DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION lkkl.let_kontrola();


--
-- Name: let let_verze; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER let_verze BEFORE UPDATE ON lkkl.let FOR EACH ROW EXECUTE FUNCTION lkkl.let_verze();


--
-- Name: lov_osoba lov_osoba_email_u_uctu; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER lov_osoba_email_u_uctu BEFORE UPDATE OF email ON lkkl.lov_osoba FOR EACH ROW EXECUTE FUNCTION lkkl.lov_osoba_email_u_uctu();


--
-- Name: nastaveni nastaveni_nemazat; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER nastaveni_nemazat BEFORE DELETE OR TRUNCATE ON lkkl.nastaveni FOR EACH STATEMENT EXECUTE FUNCTION lkkl.nevyprazdnovat();


--
-- Name: lov_role platnost_funkce; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER platnost_funkce BEFORE INSERT OR UPDATE OF funkce_id ON lkkl.lov_role FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('funkce_id', 'lov_funkce', 'Funkce');


--
-- Name: lov_ucel_funkce platnost_funkce; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER platnost_funkce BEFORE INSERT OR UPDATE OF funkce_id ON lkkl.lov_ucel_funkce FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('funkce_id', 'lov_funkce', 'Funkce');


--
-- Name: posadka platnost_funkce; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER platnost_funkce BEFORE INSERT OR UPDATE OF funkce_id ON lkkl.posadka FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('funkce_id', 'lov_funkce', 'Funkce');


--
-- Name: lov_opravneni_kategorie platnost_kategorie; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER platnost_kategorie BEFORE INSERT OR UPDATE OF kategorie_id ON lkkl.lov_opravneni_kategorie FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('kategorie_id', 'lov_kategorie', 'Kategorie');


--
-- Name: lov_osnova platnost_kategorie; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER platnost_kategorie BEFORE INSERT OR UPDATE OF kategorie_id ON lkkl.lov_osnova FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('kategorie_id', 'lov_kategorie', 'Kategorie');


--
-- Name: lov_prezkouseni platnost_kategorie; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER platnost_kategorie BEFORE INSERT OR UPDATE OF kategorie_id ON lkkl.lov_prezkouseni FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('kategorie_id', 'lov_kategorie', 'Kategorie');


--
-- Name: lov_typ platnost_kategorie; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER platnost_kategorie BEFORE INSERT OR UPDATE OF kategorie_id ON lkkl.lov_typ FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('kategorie_id', 'lov_kategorie', 'Kategorie');


--
-- Name: let platnost_letadlo; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER platnost_letadlo BEFORE INSERT OR UPDATE OF letadlo_id ON lkkl.let FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('letadlo_id', 'lov_letadlo', 'Letadlo');


--
-- Name: relace_provoz platnost_letiste; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER platnost_letiste BEFORE INSERT OR UPDATE OF letiste_id ON lkkl.relace_provoz FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('letiste_id', 'lov_letiste', 'Letiště');


--
-- Name: let platnost_misto_pristani; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER platnost_misto_pristani BEFORE INSERT OR UPDATE OF misto_pristani_id ON lkkl.let FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('misto_pristani_id', 'lov_letiste', 'Letiště');


--
-- Name: let platnost_misto_vzletu; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER platnost_misto_vzletu BEFORE INSERT OR UPDATE OF misto_vzletu_id ON lkkl.let FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('misto_vzletu_id', 'lov_letiste', 'Letiště');


--
-- Name: email platnost_odeslal; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER platnost_odeslal BEFORE INSERT OR UPDATE OF odeslal_id ON lkkl.email FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('odeslal_id', 'lov_osoba', 'Osoba');


--
-- Name: lov_opravneni_kategorie platnost_opravneni; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER platnost_opravneni BEFORE INSERT OR UPDATE OF opravneni_id ON lkkl.lov_opravneni_kategorie FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('opravneni_id', 'lov_opravneni', 'Oprávnění');


--
-- Name: lov_opravneni_role platnost_opravneni; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER platnost_opravneni BEFORE INSERT OR UPDATE OF opravneni_id ON lkkl.lov_opravneni_role FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('opravneni_id', 'lov_opravneni', 'Oprávnění');


--
-- Name: lov_osoba_opravneni platnost_opravneni; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER platnost_opravneni BEFORE INSERT OR UPDATE OF opravneni_id ON lkkl.lov_osoba_opravneni FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('opravneni_id', 'lov_opravneni', 'Oprávnění');


--
-- Name: lov_prezkouseni_opravneni platnost_opravneni; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER platnost_opravneni BEFORE INSERT OR UPDATE OF opravneni_id ON lkkl.lov_prezkouseni_opravneni FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('opravneni_id', 'lov_opravneni', 'Oprávnění');


--
-- Name: lov_uloha platnost_osnova; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER platnost_osnova BEFORE INSERT OR UPDATE OF osnova_id ON lkkl.lov_uloha FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('osnova_id', 'lov_osnova', 'Osnova');


--
-- Name: email platnost_osoba; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER platnost_osoba BEFORE INSERT OR UPDATE OF osoba_id ON lkkl.email FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('osoba_id', 'lov_osoba', 'Osoba');


--
-- Name: posadka platnost_osoba; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER platnost_osoba BEFORE INSERT OR UPDATE OF osoba_id ON lkkl.posadka FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('osoba_id', 'lov_osoba', 'Osoba');


--
-- Name: relace_provoz_osoba platnost_osoba; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER platnost_osoba BEFORE INSERT OR UPDATE OF osoba_id ON lkkl.relace_provoz_osoba FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('osoba_id', 'lov_osoba', 'Osoba');


--
-- Name: let platnost_platce; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER platnost_platce BEFORE INSERT OR UPDATE OF platce_id ON lkkl.let FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('platce_id', 'lov_osoba', 'Osoba');


--
-- Name: let platnost_prezkouseni; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER platnost_prezkouseni BEFORE INSERT OR UPDATE OF prezkouseni_id ON lkkl.let FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('prezkouseni_id', 'lov_prezkouseni', 'Přezkoušení');


--
-- Name: lov_prezkouseni_opravneni platnost_prezkouseni; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER platnost_prezkouseni BEFORE INSERT OR UPDATE OF prezkouseni_id ON lkkl.lov_prezkouseni_opravneni FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('prezkouseni_id', 'lov_prezkouseni', 'Přezkoušení');


--
-- Name: lov_opravneni_role platnost_role; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER platnost_role BEFORE INSERT OR UPDATE OF role_id ON lkkl.lov_opravneni_role FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('role_id', 'lov_role', 'Role');


--
-- Name: lov_letadlo platnost_typ; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER platnost_typ BEFORE INSERT OR UPDATE OF typ_id ON lkkl.lov_letadlo FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('typ_id', 'lov_typ', 'Typ');


--
-- Name: let platnost_ucel; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER platnost_ucel BEFORE INSERT OR UPDATE OF ucel_id ON lkkl.let FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('ucel_id', 'lov_ucel', 'Účel');


--
-- Name: lov_role platnost_ucel; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER platnost_ucel BEFORE INSERT OR UPDATE OF ucel_id ON lkkl.lov_role FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('ucel_id', 'lov_ucel', 'Účel');


--
-- Name: lov_ucel_funkce platnost_ucel; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER platnost_ucel BEFORE INSERT OR UPDATE OF ucel_id ON lkkl.lov_ucel_funkce FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('ucel_id', 'lov_ucel', 'Účel');


--
-- Name: lov_uloha_ucel platnost_ucel; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER platnost_ucel BEFORE INSERT OR UPDATE OF ucel_id ON lkkl.lov_uloha_ucel FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('ucel_id', 'lov_ucel', 'Účel');


--
-- Name: let platnost_uloha; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER platnost_uloha BEFORE INSERT OR UPDATE OF uloha_id ON lkkl.let FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('uloha_id', 'lov_uloha', 'Úloha');


--
-- Name: lov_uloha_ucel platnost_uloha; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER platnost_uloha BEFORE INSERT OR UPDATE OF uloha_id ON lkkl.lov_uloha_ucel FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('uloha_id', 'lov_uloha', 'Úloha');


--
-- Name: let platnost_zalozil; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER platnost_zalozil BEFORE INSERT OR UPDATE OF zalozil_id ON lkkl.let FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('zalozil_id', 'lov_osoba', 'Osoba');


--
-- Name: let platnost_zpusob_vzletu; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER platnost_zpusob_vzletu BEFORE INSERT OR UPDATE OF zpusob_vzletu_id ON lkkl.let FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('zpusob_vzletu_id', 'lov_zpusob_vzletu', 'Způsob vzletu');


--
-- Name: let platnost_zruseni_duvod; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER platnost_zruseni_duvod BEFORE INSERT OR UPDATE OF zruseni_duvod_id ON lkkl.let FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('zruseni_duvod_id', 'lov_duvod_zruseni', 'Důvod zrušení');


--
-- Name: let platnost_zrusil; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER platnost_zrusil BEFORE INSERT OR UPDATE OF zrusil_id ON lkkl.let FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('zrusil_id', 'lov_osoba', 'Osoba');


--
-- Name: posadka posadka_kontrola; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE CONSTRAINT TRIGGER posadka_kontrola AFTER INSERT OR DELETE OR UPDATE ON lkkl.posadka DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION lkkl.let_kontrola();


--
-- Name: ucet ucet_osoba_ma_email; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER ucet_osoba_ma_email BEFORE INSERT OR UPDATE OF osoba_id ON lkkl.ucet FOR EACH ROW EXECUTE FUNCTION lkkl.ucet_osoba_ma_email();


--
-- Name: lov_osnova vycvik_kontrola; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER vycvik_kontrola BEFORE UPDATE OF kategorie_id ON lkkl.lov_osnova FOR EACH ROW EXECUTE FUNCTION lkkl.vycvik_kontrola();


--
-- Name: lov_prezkouseni vycvik_kontrola; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER vycvik_kontrola BEFORE UPDATE OF kategorie_id ON lkkl.lov_prezkouseni FOR EACH ROW EXECUTE FUNCTION lkkl.vycvik_kontrola();


--
-- Name: lov_prezkouseni_opravneni vycvik_kontrola; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER vycvik_kontrola BEFORE INSERT OR UPDATE ON lkkl.lov_prezkouseni_opravneni FOR EACH ROW EXECUTE FUNCTION lkkl.vycvik_kontrola();


--
-- Name: lov_uloha vycvik_kontrola; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER vycvik_kontrola BEFORE UPDATE OF osnova_id ON lkkl.lov_uloha FOR EACH ROW EXECUTE FUNCTION lkkl.vycvik_kontrola();


--
-- Name: lov_uloha_ucel vycvik_kontrola; Type: TRIGGER; Schema: lkkl; Owner: -
--

CREATE TRIGGER vycvik_kontrola BEFORE DELETE ON lkkl.lov_uloha_ucel FOR EACH ROW EXECUTE FUNCTION lkkl.vycvik_kontrola();


--
-- Name: audit audit_osoba_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.audit
    ADD CONSTRAINT audit_osoba_id_fkey FOREIGN KEY (osoba_id) REFERENCES lkkl.lov_osoba(id);


--
-- Name: audit audit_puvodni_osoba_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.audit
    ADD CONSTRAINT audit_puvodni_osoba_id_fkey FOREIGN KEY (puvodni_osoba_id) REFERENCES lkkl.lov_osoba(id);


--
-- Name: email email_odeslal_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.email
    ADD CONSTRAINT email_odeslal_id_fkey FOREIGN KEY (odeslal_id) REFERENCES lkkl.lov_osoba(id);


--
-- Name: email email_osoba_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.email
    ADD CONSTRAINT email_osoba_id_fkey FOREIGN KEY (osoba_id) REFERENCES lkkl.lov_osoba(id);


--
-- Name: lov_osoba_opravneni_kategorie kategorie_povolena; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_osoba_opravneni_kategorie
    ADD CONSTRAINT kategorie_povolena FOREIGN KEY (opravneni_id, kategorie_id) REFERENCES lkkl.lov_opravneni_kategorie(opravneni_id, kategorie_id);


--
-- Name: let let_letadlo_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.let
    ADD CONSTRAINT let_letadlo_id_fkey FOREIGN KEY (letadlo_id) REFERENCES lkkl.lov_letadlo(id);


--
-- Name: let let_misto_pristani_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.let
    ADD CONSTRAINT let_misto_pristani_id_fkey FOREIGN KEY (misto_pristani_id) REFERENCES lkkl.lov_letiste(id);


--
-- Name: let let_misto_vzletu_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.let
    ADD CONSTRAINT let_misto_vzletu_id_fkey FOREIGN KEY (misto_vzletu_id) REFERENCES lkkl.lov_letiste(id);


--
-- Name: let let_platce_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.let
    ADD CONSTRAINT let_platce_id_fkey FOREIGN KEY (platce_id) REFERENCES lkkl.lov_osoba(id);


--
-- Name: let let_prezkouseni_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.let
    ADD CONSTRAINT let_prezkouseni_id_fkey FOREIGN KEY (prezkouseni_id) REFERENCES lkkl.lov_prezkouseni(id);


--
-- Name: let_tg let_tg_let_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.let_tg
    ADD CONSTRAINT let_tg_let_id_fkey FOREIGN KEY (let_id) REFERENCES lkkl.let(id);


--
-- Name: let let_ucel_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.let
    ADD CONSTRAINT let_ucel_id_fkey FOREIGN KEY (ucel_id) REFERENCES lkkl.lov_ucel(id);


--
-- Name: let let_uloha_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.let
    ADD CONSTRAINT let_uloha_id_fkey FOREIGN KEY (uloha_id) REFERENCES lkkl.lov_uloha(id);


--
-- Name: let let_vlecny_let_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.let
    ADD CONSTRAINT let_vlecny_let_id_fkey FOREIGN KEY (vlecny_let_id) REFERENCES lkkl.let(id);


--
-- Name: let let_zalozil_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.let
    ADD CONSTRAINT let_zalozil_id_fkey FOREIGN KEY (zalozil_id) REFERENCES lkkl.lov_osoba(id);


--
-- Name: let let_zpusob_vzletu_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.let
    ADD CONSTRAINT let_zpusob_vzletu_id_fkey FOREIGN KEY (zpusob_vzletu_id) REFERENCES lkkl.lov_zpusob_vzletu(id);


--
-- Name: let let_zruseni_duvod_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.let
    ADD CONSTRAINT let_zruseni_duvod_id_fkey FOREIGN KEY (zruseni_duvod_id) REFERENCES lkkl.lov_duvod_zruseni(id);


--
-- Name: let let_zrusil_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.let
    ADD CONSTRAINT let_zrusil_id_fkey FOREIGN KEY (zrusil_id) REFERENCES lkkl.lov_osoba(id);


--
-- Name: lov_letadlo lov_letadlo_typ_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_letadlo
    ADD CONSTRAINT lov_letadlo_typ_id_fkey FOREIGN KEY (typ_id) REFERENCES lkkl.lov_typ(id);


--
-- Name: lov_opravneni_kategorie lov_opravneni_kategorie_kategorie_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_opravneni_kategorie
    ADD CONSTRAINT lov_opravneni_kategorie_kategorie_id_fkey FOREIGN KEY (kategorie_id) REFERENCES lkkl.lov_kategorie(id);


--
-- Name: lov_opravneni_kategorie lov_opravneni_kategorie_opravneni_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_opravneni_kategorie
    ADD CONSTRAINT lov_opravneni_kategorie_opravneni_id_fkey FOREIGN KEY (opravneni_id) REFERENCES lkkl.lov_opravneni(id);


--
-- Name: lov_opravneni_role lov_opravneni_role_opravneni_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_opravneni_role
    ADD CONSTRAINT lov_opravneni_role_opravneni_id_fkey FOREIGN KEY (opravneni_id) REFERENCES lkkl.lov_opravneni(id);


--
-- Name: lov_opravneni_role lov_opravneni_role_role_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_opravneni_role
    ADD CONSTRAINT lov_opravneni_role_role_id_fkey FOREIGN KEY (role_id) REFERENCES lkkl.lov_role(id);


--
-- Name: lov_osnova lov_osnova_kategorie_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_osnova
    ADD CONSTRAINT lov_osnova_kategorie_id_fkey FOREIGN KEY (kategorie_id) REFERENCES lkkl.lov_kategorie(id);


--
-- Name: lov_osoba_opravneni lov_osoba_opravneni_opravneni_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_osoba_opravneni
    ADD CONSTRAINT lov_osoba_opravneni_opravneni_id_fkey FOREIGN KEY (opravneni_id) REFERENCES lkkl.lov_opravneni(id);


--
-- Name: lov_osoba_opravneni lov_osoba_opravneni_osoba_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_osoba_opravneni
    ADD CONSTRAINT lov_osoba_opravneni_osoba_id_fkey FOREIGN KEY (osoba_id) REFERENCES lkkl.lov_osoba(id);


--
-- Name: lov_prezkouseni lov_prezkouseni_kategorie_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_prezkouseni
    ADD CONSTRAINT lov_prezkouseni_kategorie_id_fkey FOREIGN KEY (kategorie_id) REFERENCES lkkl.lov_kategorie(id);


--
-- Name: lov_prezkouseni_opravneni lov_prezkouseni_opravneni_opravneni_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_prezkouseni_opravneni
    ADD CONSTRAINT lov_prezkouseni_opravneni_opravneni_id_fkey FOREIGN KEY (opravneni_id) REFERENCES lkkl.lov_opravneni(id);


--
-- Name: lov_prezkouseni_opravneni lov_prezkouseni_opravneni_prezkouseni_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_prezkouseni_opravneni
    ADD CONSTRAINT lov_prezkouseni_opravneni_prezkouseni_id_fkey FOREIGN KEY (prezkouseni_id) REFERENCES lkkl.lov_prezkouseni(id);


--
-- Name: lov_role lov_role_funkce_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_role
    ADD CONSTRAINT lov_role_funkce_id_fkey FOREIGN KEY (funkce_id) REFERENCES lkkl.lov_funkce(id);


--
-- Name: lov_role lov_role_ucel_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_role
    ADD CONSTRAINT lov_role_ucel_id_fkey FOREIGN KEY (ucel_id) REFERENCES lkkl.lov_ucel(id);


--
-- Name: lov_typ lov_typ_kategorie_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_typ
    ADD CONSTRAINT lov_typ_kategorie_id_fkey FOREIGN KEY (kategorie_id) REFERENCES lkkl.lov_kategorie(id);


--
-- Name: lov_ucel_funkce lov_ucel_funkce_funkce_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_ucel_funkce
    ADD CONSTRAINT lov_ucel_funkce_funkce_id_fkey FOREIGN KEY (funkce_id) REFERENCES lkkl.lov_funkce(id);


--
-- Name: lov_ucel_funkce lov_ucel_funkce_ucel_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_ucel_funkce
    ADD CONSTRAINT lov_ucel_funkce_ucel_id_fkey FOREIGN KEY (ucel_id) REFERENCES lkkl.lov_ucel(id);


--
-- Name: lov_uloha lov_uloha_osnova_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_uloha
    ADD CONSTRAINT lov_uloha_osnova_id_fkey FOREIGN KEY (osnova_id) REFERENCES lkkl.lov_osnova(id);


--
-- Name: lov_uloha_ucel lov_uloha_ucel_ucel_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_uloha_ucel
    ADD CONSTRAINT lov_uloha_ucel_ucel_id_fkey FOREIGN KEY (ucel_id) REFERENCES lkkl.lov_ucel(id);


--
-- Name: lov_uloha_ucel lov_uloha_ucel_uloha_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_uloha_ucel
    ADD CONSTRAINT lov_uloha_ucel_uloha_id_fkey FOREIGN KEY (uloha_id) REFERENCES lkkl.lov_uloha(id);


--
-- Name: lov_osoba_opravneni_kategorie opravneni_osoby; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.lov_osoba_opravneni_kategorie
    ADD CONSTRAINT opravneni_osoby FOREIGN KEY (osoba_id, opravneni_id) REFERENCES lkkl.lov_osoba_opravneni(osoba_id, opravneni_id);


--
-- Name: posadka posadka_funkce_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.posadka
    ADD CONSTRAINT posadka_funkce_id_fkey FOREIGN KEY (funkce_id) REFERENCES lkkl.lov_funkce(id);


--
-- Name: posadka posadka_let_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.posadka
    ADD CONSTRAINT posadka_let_id_fkey FOREIGN KEY (let_id) REFERENCES lkkl.let(id);


--
-- Name: posadka posadka_osoba_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.posadka
    ADD CONSTRAINT posadka_osoba_id_fkey FOREIGN KEY (osoba_id) REFERENCES lkkl.lov_osoba(id);


--
-- Name: relace relace_osoba_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.relace
    ADD CONSTRAINT relace_osoba_id_fkey FOREIGN KEY (osoba_id) REFERENCES lkkl.ucet(osoba_id);


--
-- Name: relace_provoz relace_provoz_letiste_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.relace_provoz
    ADD CONSTRAINT relace_provoz_letiste_id_fkey FOREIGN KEY (letiste_id) REFERENCES lkkl.lov_letiste(id);


--
-- Name: relace_provoz_osoba relace_provoz_osoba_osoba_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.relace_provoz_osoba
    ADD CONSTRAINT relace_provoz_osoba_osoba_id_fkey FOREIGN KEY (osoba_id) REFERENCES lkkl.lov_osoba(id);


--
-- Name: relace_provoz_osoba relace_provoz_osoba_relace_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.relace_provoz_osoba
    ADD CONSTRAINT relace_provoz_osoba_relace_id_fkey FOREIGN KEY (relace_id) REFERENCES lkkl.relace_provoz(relace_id);


--
-- Name: relace_provoz relace_provoz_relace_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.relace_provoz
    ADD CONSTRAINT relace_provoz_relace_id_fkey FOREIGN KEY (relace_id) REFERENCES lkkl.relace(id);


--
-- Name: relace relace_puvodni_osoba_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.relace
    ADD CONSTRAINT relace_puvodni_osoba_id_fkey FOREIGN KEY (puvodni_osoba_id) REFERENCES lkkl.ucet(osoba_id);


--
-- Name: ucet ucet_osoba_id_fkey; Type: FK CONSTRAINT; Schema: lkkl; Owner: -
--

ALTER TABLE ONLY lkkl.ucet
    ADD CONSTRAINT ucet_osoba_id_fkey FOREIGN KEY (osoba_id) REFERENCES lkkl.lov_osoba(id);


--
-- PostgreSQL database dump complete
--


