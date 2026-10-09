-- 042: Editor výcviku – osnovy, úlohy a typy přezkoušení v aplikaci (návrh docs/modul-osnovy.md,
-- maketa docs/navrhy/osnovy-desktop-v2.html; rozhodnuto 9. 10. 2026). „Lze letět i na“ jinou
-- kategorii (lov_uloha_kategorie) zatím ne – otevřené.
--   ucet.spravuje_vycvik – jedno právo na osnovy, úlohy i typy přezkoušení (admin má vždy)
--   lov_osnova.kategorie_id povinná (osnova striktně jedné kategorie)
--   pravidla: kategorii osnovy ani typu přezkoušení s lety nejde změnit, úlohu s lety nejde
--   přesunout do osnovy jiné kategorie, účel úlohy použitý v letech nejde odebrat, typ smí
--   provést jen oprávnění vydávané pro jeho kategorii
--   audit na lov_osnova, lov_uloha, lov_uloha_ucel, lov_prezkouseni, lov_prezkouseni_opravneni
--   (bez pořadí – přečíslování je šum)

-- --- právo -------------------------------------------------------------------------------------
ALTER TABLE lkkl.ucet ADD COLUMN spravuje_vycvik boolean NOT NULL DEFAULT false;
COMMENT ON COLUMN lkkl.ucet.spravuje_vycvik IS
    'Smí spravovat osnovy, úlohy a typy přezkoušení (editor výcviku na desktopu); admin vždy.';
INSERT INTO lkkl.lov_audit_popisek (tabulka, sloupec, popisek, poradi, skryt_hodnotu)
VALUES ('ucet', 'spravuje_vycvik', 'spravuje výcvik', 37, false);

CREATE OR REPLACE VIEW lkkl.v_ucet AS
SELECT u.osoba_id, o.jmeno, o.prijmeni, o.email,
       u.heslo_hash IS NOT NULL AS ma_heslo,
       u.prihlaseni_povoleno AND o.platny AS smi_se_prihlasit,
       u.admin, u.zalozen, u.pozvanka_odeslana, u.posledni_prihlaseni, u.zablokovano_do,
       u.smi_odblokovat, u.spravuje_osoby, u.spravuje_letadla, u.spravuje_vycvik
FROM lkkl.ucet u
JOIN lkkl.lov_osoba o ON o.id = u.osoba_id;

-- --- osnova vždy jedné kategorie ----------------------------------------------------------------
ALTER TABLE lkkl.lov_osnova ALTER COLUMN kategorie_id SET NOT NULL;

-- --- pravidla: co by rozbilo staré lety ----------------------------------------------------------
CREATE FUNCTION lkkl.vycvik_kontrola() RETURNS trigger
LANGUAGE plpgsql AS $$
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
COMMENT ON FUNCTION lkkl.vycvik_kontrola() IS
    'Pravidla editoru výcviku (042): změna kategorie nebo účelu nesmí rozbít staré lety; typ přezkoušení jen s oprávněním pro jeho kategorii.';

CREATE TRIGGER vycvik_kontrola BEFORE UPDATE OF kategorie_id ON lkkl.lov_osnova
    FOR EACH ROW EXECUTE FUNCTION lkkl.vycvik_kontrola();
CREATE TRIGGER vycvik_kontrola BEFORE UPDATE OF osnova_id ON lkkl.lov_uloha
    FOR EACH ROW EXECUTE FUNCTION lkkl.vycvik_kontrola();
CREATE TRIGGER vycvik_kontrola BEFORE DELETE ON lkkl.lov_uloha_ucel
    FOR EACH ROW EXECUTE FUNCTION lkkl.vycvik_kontrola();
CREATE TRIGGER vycvik_kontrola BEFORE UPDATE OF kategorie_id ON lkkl.lov_prezkouseni
    FOR EACH ROW EXECUTE FUNCTION lkkl.vycvik_kontrola();
CREATE TRIGGER vycvik_kontrola BEFORE INSERT OR UPDATE ON lkkl.lov_prezkouseni_opravneni
    FOR EACH ROW EXECUTE FUNCTION lkkl.vycvik_kontrola();

-- --- audit -------------------------------------------------------------------------------------
CREATE TRIGGER audit AFTER INSERT OR UPDATE OR DELETE ON lkkl.lov_osnova
    FOR EACH ROW EXECUTE FUNCTION lkkl.audit_zapsat('poradi');
CREATE TRIGGER audit AFTER INSERT OR UPDATE OR DELETE ON lkkl.lov_uloha
    FOR EACH ROW EXECUTE FUNCTION lkkl.audit_zapsat('poradi');
CREATE TRIGGER audit AFTER INSERT OR UPDATE OR DELETE ON lkkl.lov_uloha_ucel
    FOR EACH ROW EXECUTE FUNCTION lkkl.audit_zapsat();
CREATE TRIGGER audit AFTER INSERT OR UPDATE OR DELETE ON lkkl.lov_prezkouseni
    FOR EACH ROW EXECUTE FUNCTION lkkl.audit_zapsat('poradi');
CREATE TRIGGER audit AFTER INSERT OR UPDATE OR DELETE ON lkkl.lov_prezkouseni_opravneni
    FOR EACH ROW EXECUTE FUNCTION lkkl.audit_zapsat();

INSERT INTO lkkl.lov_audit_popisek (tabulka, sloupec, popisek, poradi, skryt_hodnotu) VALUES
    ('lov_osnova', 'kod', 'označení', 10, false),
    ('lov_osnova', 'nazev', 'název', 20, false),
    ('lov_osnova', 'kategorie_id', 'kategorie', 30, false),
    ('lov_osnova', 'platny', 'platná', 40, false),
    ('lov_uloha', 'osnova_id', 'osnova', 10, false),
    ('lov_uloha', 'kod', 'označení', 20, false),
    ('lov_uloha', 'nazev', 'název', 30, false),
    ('lov_uloha', 'platny', 'platná', 40, false),
    ('lov_uloha_ucel', 'uloha_id', 'úloha', 10, false),
    ('lov_uloha_ucel', 'ucel_id', 'účel', 20, false),
    ('lov_prezkouseni', 'kod', 'kód', 10, false),
    ('lov_prezkouseni', 'nazev', 'název', 20, false),
    ('lov_prezkouseni', 'kategorie_id', 'kategorie', 30, false),
    ('lov_prezkouseni', 'platny', 'platný', 40, false),
    ('lov_prezkouseni_opravneni', 'prezkouseni_id', 'přezkoušení', 10, false),
    ('lov_prezkouseni_opravneni', 'opravneni_id', 'oprávnění', 20, false);

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
        ELSE p_operace
    END
$$;

-- čitelná hodnota osnovy (přesun úlohy)
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
        WHEN p_sloupec = 'osnova_id' THEN
            (SELECT kod || ' – ' || nazev FROM lkkl.lov_osnova WHERE id = (p_hodnota #>> '{}')::bigint)
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
