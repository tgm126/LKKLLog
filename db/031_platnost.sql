-- 031: Platnost záznamu – jeden standard pro všechny tabulky lov_ s vlastním id (návrh
-- odsouhlasen 8. 10. 2026, CLAUDE.md bod 10). Sloupec platny (doména lkkl.platny): neplatný
-- záznam zůstává v databázi jen kvůli starým vazbám, nikde se nenabízí (pohledy v_lov_*)
-- a nejde ho nově použít (trigger kontrola_platnosti). Platnost se nedědí.
-- Bez platnosti zůstávají vazební tabulky (nic na ně neodkazuje, vazba se smaže)
-- a lov_audit_popisek.

-- --- osoba: aktivni → platny (stejný význam) ------------------------------------------------
-- Pohledy nad sloupcem se musí založit znovu (změna typu na doménu).
DROP VIEW lkkl.v_ucet;
DROP VIEW lkkl.v_osoba_opravneni;

ALTER TABLE lkkl.lov_osoba RENAME COLUMN aktivni TO platny;
ALTER TABLE lkkl.lov_osoba ALTER COLUMN platny DROP DEFAULT;
ALTER TABLE lkkl.lov_osoba ALTER COLUMN platny TYPE lkkl.platny;

COMMENT ON COLUMN lkkl.lov_osoba.platny IS
    'Ne = bývalý člen nebo už nelétá: nenabízí se, nesmí se přihlásit, nejde nově použít; '
    'zůstává kvůli historii letů. V aplikaci „aktivní“.';

CREATE VIEW lkkl.v_ucet AS
SELECT u.osoba_id, o.jmeno, o.prijmeni, o.email,
       u.heslo_hash IS NOT NULL AS ma_heslo,
       u.aktivni AND o.platny AS smi_se_prihlasit,
       u.admin, u.zalozen, u.pozvanka_odeslana, u.posledni_prihlaseni, u.zablokovano_do,
       u.smi_odblokovat, u.spravuje_osoby, u.spravuje_letadla
FROM lkkl.ucet u
JOIN lkkl.lov_osoba o ON o.id = u.osoba_id;

COMMENT ON VIEW lkkl.v_ucet IS
    'Účty s údaji osoby (bez otisku hesla); smí se přihlásit = účet aktivní a osoba platná.';

-- přehled oprávnění pro správce databáze (všechny osoby, i neplatné)
CREATE VIEW lkkl.v_osoba_opravneni AS
SELECT os.id, os.prijmeni, os.jmeno, os.platny,
       string_agg(o.nazev || ' (' || coalesce(ok.kategorie, '–')
                  || CASE WHEN oo.omezene THEN '; omezené' ELSE '' END || ')',
                  ', ' ORDER BY o.poradi) AS opravneni
FROM lkkl.lov_osoba os
LEFT JOIN lkkl.lov_osoba_opravneni oo ON oo.osoba_id = os.id
LEFT JOIN lkkl.lov_opravneni o ON o.id = oo.opravneni_id
LEFT JOIN LATERAL (
    SELECT string_agg(k.nazev, ', ' ORDER BY k.poradi) AS kategorie
    FROM lkkl.lov_osoba_opravneni_kategorie x
    JOIN lkkl.lov_kategorie k ON k.id = x.kategorie_id
    WHERE x.osoba_id = oo.osoba_id AND x.opravneni_id = oo.opravneni_id
) ok ON true
GROUP BY os.id
ORDER BY os.prijmeni, os.jmeno;

COMMENT ON VIEW lkkl.v_osoba_opravneni IS
    'Přehled oprávnění osob s kategoriemi a omezením (kontrola zadání); i neplatné osoby.';

-- popisek pro audit (starý „aktivni“ zůstává kvůli dřívějším záznamům)
INSERT INTO lkkl.lov_audit_popisek (tabulka, sloupec, popisek, poradi, skryt_hodnotu)
VALUES ('lov_osoba', 'platny', 'aktivní', 70, false);

-- --- letadlo: platny vedle mimo_provoz ---------------------------------------------------------
-- mimo_provoz = dočasně nelétá (vidět šedě, nejde vybrat); platny = vyřazené (prodané) –
-- nikde se neukáže. Vyřazuje se zatím jen přímo v databázi.
ALTER TABLE lkkl.lov_letadlo ADD COLUMN platny lkkl.platny NOT NULL;

COMMENT ON COLUMN lkkl.lov_letadlo.platny IS
    'Ne = vyřazené (prodané, zrušené): nikde se neukazuje, nejde nově použít; zůstává kvůli '
    'historii letů. Dočasný stav je mimo_provoz.';

INSERT INTO lkkl.lov_audit_popisek (tabulka, sloupec, popisek, poradi, skryt_hodnotu)
VALUES ('lov_letadlo', 'platny', 'platné (nevyřazené)', 65, false);

CREATE OR REPLACE VIEW lkkl.v_lov_letadlo AS
SELECT l.id, l.rejstrik, t.nazev AS typ, k.nazev AS kategorie, k.kod AS kategorie_kod,
       t.pocet_mist, l.max_doba_min, l.vlecne, l.soukrome, l.mimo_provoz
FROM lkkl.lov_letadlo l
JOIN lkkl.lov_typ t ON t.id = l.typ_id
JOIN lkkl.lov_kategorie k ON k.id = t.kategorie_id
WHERE l.platny
ORDER BY k.poradi, t.poradi, t.nazev, l.rejstrik;

COMMENT ON VIEW lkkl.v_lov_letadlo IS
    'Platná letadla pro nabídky a obrazovky: typ, kategorie, počet míst; i mimo provoz '
    '(zobrazí se, nejdou vybrat). Vyřazená (neplatná) se neukazují nikde.';

-- --- role osob: jen platné kategorie, funkce a účely (nabídka posádky) -----------------------
CREATE OR REPLACE VIEW lkkl.v_osoba_smi AS
SELECT DISTINCT oo.osoba_id, r.kod AS role_kod, u.kod AS ucel_kod, f.kod AS funkce_kod,
       k.kod AS kategorie_kod
FROM lkkl.lov_osoba_opravneni oo
JOIN lkkl.lov_opravneni o ON o.id = oo.opravneni_id AND o.platny
JOIN lkkl.lov_osoba_opravneni_kategorie ok
  ON ok.osoba_id = oo.osoba_id AND ok.opravneni_id = oo.opravneni_id
JOIN lkkl.lov_kategorie k ON k.id = ok.kategorie_id AND k.platny
JOIN lkkl.lov_opravneni_role orl ON orl.opravneni_id = oo.opravneni_id
JOIN lkkl.lov_role r ON r.id = orl.role_id AND r.platny
LEFT JOIN lkkl.lov_ucel u ON u.id = r.ucel_id
JOIN lkkl.lov_funkce f ON f.id = r.funkce_id AND f.platny
WHERE r.ucel_id IS NULL OR u.platny;

COMMENT ON VIEW lkkl.v_osoba_smi IS
    'Role, které osoba smí zastat: role, účel (prázdný = vlečný let), funkce a kategorie '
    'letadla – jen platné položky číselníků.';

-- --- nejde nově použít: kontrola každé nové nebo změněné vazby ---------------------------------
-- Argumenty: sloupec s cizím klíčem, tabulka lov_, popis pro hlášku. Stará vazba se při úpravě
-- jiného sloupce nekontroluje (úprava starého letu projde); zachytí i zápis přímo v databázi.
CREATE FUNCTION lkkl.kontrola_platnosti() RETURNS trigger
LANGUAGE plpgsql AS $$
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
END $$;

COMMENT ON FUNCTION lkkl.kontrola_platnosti() IS
    'Trigger: nová nebo změněná vazba nesmí vést na neplatný záznam lov_ (sloupec, tabulka, popis).';

-- provozní data
CREATE TRIGGER platnost_letadlo BEFORE INSERT OR UPDATE OF letadlo_id ON lkkl.let
    FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('letadlo_id', 'lov_letadlo', 'Letadlo');
CREATE TRIGGER platnost_ucel BEFORE INSERT OR UPDATE OF ucel_id ON lkkl.let
    FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('ucel_id', 'lov_ucel', 'Účel');
CREATE TRIGGER platnost_zpusob_vzletu BEFORE INSERT OR UPDATE OF zpusob_vzletu_id ON lkkl.let
    FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('zpusob_vzletu_id', 'lov_zpusob_vzletu', 'Způsob vzletu');
CREATE TRIGGER platnost_uloha BEFORE INSERT OR UPDATE OF uloha_id ON lkkl.let
    FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('uloha_id', 'lov_uloha', 'Úloha');
CREATE TRIGGER platnost_misto_vzletu BEFORE INSERT OR UPDATE OF misto_vzletu_id ON lkkl.let
    FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('misto_vzletu_id', 'lov_letiste', 'Letiště');
CREATE TRIGGER platnost_misto_pristani BEFORE INSERT OR UPDATE OF misto_pristani_id ON lkkl.let
    FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('misto_pristani_id', 'lov_letiste', 'Letiště');
CREATE TRIGGER platnost_zruseni_duvod BEFORE INSERT OR UPDATE OF zruseni_duvod_id ON lkkl.let
    FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('zruseni_duvod_id', 'lov_duvod_zruseni', 'Důvod zrušení');
CREATE TRIGGER platnost_platce BEFORE INSERT OR UPDATE OF platce_id ON lkkl.let
    FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('platce_id', 'lov_osoba', 'Osoba');
CREATE TRIGGER platnost_zalozil BEFORE INSERT OR UPDATE OF zalozil_id ON lkkl.let
    FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('zalozil_id', 'lov_osoba', 'Osoba');
CREATE TRIGGER platnost_zrusil BEFORE INSERT OR UPDATE OF zrusil_id ON lkkl.let
    FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('zrusil_id', 'lov_osoba', 'Osoba');
CREATE TRIGGER platnost_osoba BEFORE INSERT OR UPDATE OF osoba_id ON lkkl.posadka
    FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('osoba_id', 'lov_osoba', 'Osoba');
CREATE TRIGGER platnost_funkce BEFORE INSERT OR UPDATE OF funkce_id ON lkkl.posadka
    FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('funkce_id', 'lov_funkce', 'Funkce');
CREATE TRIGGER platnost_letiste BEFORE INSERT OR UPDATE OF letiste_id ON lkkl.relace_provoz
    FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('letiste_id', 'lov_letiste', 'Letiště');
CREATE TRIGGER platnost_osoba BEFORE INSERT OR UPDATE OF osoba_id ON lkkl.relace_provoz_osoba
    FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('osoba_id', 'lov_osoba', 'Osoba');

-- vazby mezi číselníky (zachytí hlavně ruční zápis v databázi). Bez kontroly zůstává osoba
-- u svého účtu a oprávnění (údaje osoby, ne její použití).
CREATE TRIGGER platnost_typ BEFORE INSERT OR UPDATE OF typ_id ON lkkl.lov_letadlo
    FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('typ_id', 'lov_typ', 'Typ');
CREATE TRIGGER platnost_kategorie BEFORE INSERT OR UPDATE OF kategorie_id ON lkkl.lov_typ
    FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('kategorie_id', 'lov_kategorie', 'Kategorie');
CREATE TRIGGER platnost_kategorie BEFORE INSERT OR UPDATE OF kategorie_id ON lkkl.lov_osnova
    FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('kategorie_id', 'lov_kategorie', 'Kategorie');
CREATE TRIGGER platnost_osnova BEFORE INSERT OR UPDATE OF osnova_id ON lkkl.lov_uloha
    FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('osnova_id', 'lov_osnova', 'Osnova');
CREATE TRIGGER platnost_funkce BEFORE INSERT OR UPDATE OF funkce_id ON lkkl.lov_role
    FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('funkce_id', 'lov_funkce', 'Funkce');
CREATE TRIGGER platnost_ucel BEFORE INSERT OR UPDATE OF ucel_id ON lkkl.lov_role
    FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('ucel_id', 'lov_ucel', 'Účel');
CREATE TRIGGER platnost_ucel BEFORE INSERT OR UPDATE OF ucel_id ON lkkl.lov_ucel_funkce
    FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('ucel_id', 'lov_ucel', 'Účel');
CREATE TRIGGER platnost_funkce BEFORE INSERT OR UPDATE OF funkce_id ON lkkl.lov_ucel_funkce
    FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('funkce_id', 'lov_funkce', 'Funkce');
CREATE TRIGGER platnost_uloha BEFORE INSERT OR UPDATE OF uloha_id ON lkkl.lov_uloha_ucel
    FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('uloha_id', 'lov_uloha', 'Úloha');
CREATE TRIGGER platnost_ucel BEFORE INSERT OR UPDATE OF ucel_id ON lkkl.lov_uloha_ucel
    FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('ucel_id', 'lov_ucel', 'Účel');
CREATE TRIGGER platnost_opravneni BEFORE INSERT OR UPDATE OF opravneni_id ON lkkl.lov_opravneni_kategorie
    FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('opravneni_id', 'lov_opravneni', 'Oprávnění');
CREATE TRIGGER platnost_kategorie BEFORE INSERT OR UPDATE OF kategorie_id ON lkkl.lov_opravneni_kategorie
    FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('kategorie_id', 'lov_kategorie', 'Kategorie');
CREATE TRIGGER platnost_opravneni BEFORE INSERT OR UPDATE OF opravneni_id ON lkkl.lov_opravneni_role
    FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('opravneni_id', 'lov_opravneni', 'Oprávnění');
CREATE TRIGGER platnost_role BEFORE INSERT OR UPDATE OF role_id ON lkkl.lov_opravneni_role
    FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('role_id', 'lov_role', 'Role');
CREATE TRIGGER platnost_opravneni BEFORE INSERT OR UPDATE OF opravneni_id ON lkkl.lov_osoba_opravneni
    FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('opravneni_id', 'lov_opravneni', 'Oprávnění');
