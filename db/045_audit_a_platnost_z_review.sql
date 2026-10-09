-- 045: Drobnosti z code review 9. 10. 2026 (docs/code-review-2026-10-09.md, D5, D6, D9):
--   D5  popis změny v auditu nepřijde o hodnotu, když cíl vazby už neexistuje (smazaný vlečný
--       let → „vlečná #123“ místo vynechané položky);
--   D6  audit i u druhů oprávnění a jejich vazeb (kategorie, role) – rozhodují, kdo se nabídne
--       jako instruktor, examinátor, vlekař; zatím se mění jen přímo v databázi, tím spíš;
--   D9  odkaz pro heslo nejde poslat neplatné osobě (kontrola platnosti na lkkl.email)
--       a jediný řádek nastavení nejde smazat.

-- --- D5: hodnota v auditu, i když cíl vazby zmizel --------------------------------------------
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
            to_char((p_hodnota #>> '{}')::timestamptz AT TIME ZONE 'UTC', 'HH24:MI:SS')
        WHEN p_sloupec IN ('pozvanka_odeslana', 'zablokovano_do') THEN
            to_char((p_hodnota #>> '{}')::timestamptz AT TIME ZONE 'UTC', 'FMDD. FMMM. YYYY HH24:MI')
        ELSE p_hodnota #>> '{}'
    END, '#' || (p_hodnota #>> '{}'))  -- cíl vazby už neexistuje: aspoň jeho id
$$;

-- --- D6: audit druhů oprávnění a jejich vazeb ------------------------------------------------
CREATE TRIGGER audit AFTER INSERT OR UPDATE OR DELETE ON lkkl.lov_opravneni
    FOR EACH ROW EXECUTE FUNCTION lkkl.audit_zapsat('poradi');
CREATE TRIGGER audit AFTER INSERT OR UPDATE OR DELETE ON lkkl.lov_opravneni_kategorie
    FOR EACH ROW EXECUTE FUNCTION lkkl.audit_zapsat();
CREATE TRIGGER audit AFTER INSERT OR UPDATE OR DELETE ON lkkl.lov_opravneni_role
    FOR EACH ROW EXECUTE FUNCTION lkkl.audit_zapsat();

INSERT INTO lkkl.lov_audit_popisek (tabulka, sloupec, popisek, poradi, skryt_hodnotu) VALUES
    ('lov_opravneni', 'kod', 'kód', 10, false),
    ('lov_opravneni', 'nazev', 'název', 20, false),
    ('lov_opravneni', 'platny', 'platné', 30, false),
    ('lov_opravneni_kategorie', 'opravneni_id', 'oprávnění', 10, false),
    ('lov_opravneni_kategorie', 'kategorie_id', 'kategorie', 20, false),
    ('lov_opravneni_role', 'opravneni_id', 'oprávnění', 10, false),
    ('lov_opravneni_role', 'ucel_id', 'účel', 20, false),
    ('lov_opravneni_role', 'funkce_id', 'funkce', 30, false);

CREATE OR REPLACE FUNCTION lkkl.audit_akce(p_tabulka text, p_operace text, z jsonb)
 RETURNS text
 LANGUAGE sql
 IMMUTABLE
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

-- --- D9: platnost osob u e-mailu, nastavení nejde smazat ------------------------------------
CREATE TRIGGER platnost_osoba BEFORE INSERT OR UPDATE OF osoba_id ON lkkl.email
    FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('osoba_id', 'lov_osoba', 'Osoba');
CREATE TRIGGER platnost_odeslal BEFORE INSERT OR UPDATE OF odeslal_id ON lkkl.email
    FOR EACH ROW EXECUTE FUNCTION lkkl.kontrola_platnosti('odeslal_id', 'lov_osoba', 'Osoba');

CREATE TRIGGER nastaveni_nemazat BEFORE DELETE OR TRUNCATE ON lkkl.nastaveni
    FOR EACH STATEMENT EXECUTE FUNCTION lkkl.nevyprazdnovat();
