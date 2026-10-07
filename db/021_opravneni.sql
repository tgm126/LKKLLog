-- 021: oprávnění osob (instruktor, examinátor, vlekař…) – číselník a vazby. Slouží jen
-- k nabídkám osob při zakládání letu (instruktor u výcviku, examinátor u přezkoušení, vlekař
-- u vleku); nic se nekontroluje ani neblokuje, platnost se neeviduje.
-- Druhy oprávnění podle docs/podklady/instruktori-a-examinatori.md; naplnění 021_opravneni_data.sql.

CREATE TABLE lkkl.lov_opravneni (
    id        bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    kod       lkkl.kod    NOT NULL UNIQUE,
    nazev     lkkl.nazev  NOT NULL,
    poradi    lkkl.poradi NOT NULL,
    platny    lkkl.platny NOT NULL,
    vycvik    boolean     NOT NULL DEFAULT false,
    prezkousi boolean     NOT NULL DEFAULT false,
    vleka     boolean     NOT NULL DEFAULT false,
    omezene   boolean     NOT NULL DEFAULT false
);
COMMENT ON TABLE lkkl.lov_opravneni IS 'Druh oprávnění osoby (FI(S), FE(S), FI(A), vlekař…) – určuje, koho nabídnout v posádce.';
COMMENT ON COLUMN lkkl.lov_opravneni.vycvik IS 'Smí vést výcvik (instruktor u výcviku, dozor u sóla).';
COMMENT ON COLUMN lkkl.lov_opravneni.prezkousi IS 'Smí přezkoušet (examinátor u přezkoušení).';
COMMENT ON COLUMN lkkl.lov_opravneni.vleka IS 'Smí vlekat (vlekař u aerovleku).';
COMMENT ON COLUMN lkkl.lov_opravneni.omezene IS 'Omezené oprávnění (instruktor pod dohledem) – zatím jen evidence, aplikace ho nepoužívá.';

CREATE TABLE lkkl.lov_opravneni_kategorie (
    opravneni_id bigint NOT NULL REFERENCES lkkl.lov_opravneni,
    kategorie_id bigint NOT NULL REFERENCES lkkl.lov_kategorie,
    PRIMARY KEY (opravneni_id, kategorie_id)
);
COMMENT ON TABLE lkkl.lov_opravneni_kategorie IS 'Pro které kategorie letadel oprávnění platí; bez řádku platí pro všechny kategorie.';
CREATE INDEX lov_opravneni_kategorie_kategorie ON lkkl.lov_opravneni_kategorie (kategorie_id);

CREATE TABLE lkkl.lov_osoba_opravneni (
    osoba_id     bigint NOT NULL REFERENCES lkkl.lov_osoba,
    opravneni_id bigint NOT NULL REFERENCES lkkl.lov_opravneni,
    PRIMARY KEY (osoba_id, opravneni_id)
);
COMMENT ON TABLE lkkl.lov_osoba_opravneni IS 'Kdo má jaké oprávnění (zadává správce přímo v databázi).';
CREATE INDEX lov_osoba_opravneni_opravneni ON lkkl.lov_osoba_opravneni (opravneni_id);

-- Vlekař: dosavadní příznak osoby se převede na oprávnění (bez kategorií = vleká čímkoli).
INSERT INTO lkkl.lov_opravneni (kod, nazev, poradi, vleka) VALUES ('VLEKAR', 'Vlekař', 900, true);
INSERT INTO lkkl.lov_osoba_opravneni (osoba_id, opravneni_id)
SELECT o.id, (SELECT id FROM lkkl.lov_opravneni WHERE kod = 'VLEKAR')
FROM lkkl.lov_osoba o WHERE o.vlekar;
ALTER TABLE lkkl.lov_osoba DROP COLUMN vlekar;
DELETE FROM lkkl.lov_audit_popisek WHERE tabulka = 'lov_osoba' AND sloupec = 'vlekar';

-- Nabídka číselníku (standard) a co osoba smí podle platných oprávnění.
CREATE VIEW lkkl.v_lov_opravneni AS
SELECT * FROM lkkl.lov_opravneni WHERE platny ORDER BY poradi, nazev;

CREATE VIEW lkkl.v_osoba_smi AS
SELECT oo.osoba_id, o.vycvik, o.prezkousi, o.vleka, o.omezene, k.kod AS kategorie_kod
FROM lkkl.lov_osoba_opravneni oo
JOIN lkkl.lov_opravneni o               ON o.id = oo.opravneni_id AND o.platny
LEFT JOIN lkkl.lov_opravneni_kategorie ok ON ok.opravneni_id = o.id
LEFT JOIN lkkl.lov_kategorie k           ON k.id = ok.kategorie_id;
COMMENT ON VIEW lkkl.v_osoba_smi IS 'Co osoba smí (výcvik, přezkoušení, vlekání) a pro kterou kategorii; prázdná kategorie = všechny.';

-- Pro kontrolu v databázi: osoby a jejich oprávnění v jednom řádku.
CREATE VIEW lkkl.v_osoba_opravneni AS
SELECT os.id, os.prijmeni, os.jmeno, os.aktivni,
       string_agg(o.nazev, ', ' ORDER BY o.poradi) AS opravneni
FROM lkkl.lov_osoba os
LEFT JOIN lkkl.lov_osoba_opravneni oo ON oo.osoba_id = os.id
LEFT JOIN lkkl.lov_opravneni o        ON o.id = oo.opravneni_id
GROUP BY os.id
ORDER BY os.prijmeni, os.jmeno;
COMMENT ON VIEW lkkl.v_osoba_opravneni IS 'Přehled oprávnění osob (kontrola zadání).';

-- Audit: kdo komu oprávnění přidal nebo odebral.
CREATE TRIGGER audit AFTER INSERT OR UPDATE OR DELETE ON lkkl.lov_osoba_opravneni
    FOR EACH ROW EXECUTE FUNCTION lkkl.audit_zapsat();
INSERT INTO lkkl.lov_audit_popisek (tabulka, sloupec, popisek, poradi) VALUES
    ('lov_osoba_opravneni', 'osoba_id', 'osoba', 10),
    ('lov_osoba_opravneni', 'opravneni_id', 'oprávnění', 20);

CREATE OR REPLACE FUNCTION lkkl.audit_hodnota(p_sloupec text, p_hodnota jsonb)
 RETURNS text
 LANGUAGE sql
 STABLE
AS $function$
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
            (SELECT nazev FROM lkkl.lov_uloha WHERE id = (p_hodnota #>> '{}')::bigint)
        WHEN p_sloupec = 'opravneni_id' THEN
            (SELECT nazev FROM lkkl.lov_opravneni WHERE id = (p_hodnota #>> '{}')::bigint)
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
$function$;

CREATE OR REPLACE FUNCTION lkkl.audit_akce(p_tabulka text, p_operace text, z jsonb)
 RETURNS text
 LANGUAGE sql
 IMMUTABLE
AS $function$
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
        WHEN 'lov_osoba_opravneni' THEN CASE p_operace
            WHEN 'INSERT' THEN 'Přidání oprávnění' WHEN 'DELETE' THEN 'Odebrání oprávnění' ELSE 'Úprava oprávnění' END
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
        WHEN 'lov_letadlo' THEN CASE p_operace
            WHEN 'INSERT' THEN 'Založení letadla' WHEN 'DELETE' THEN 'Smazání letadla' ELSE 'Úprava letadla' END
        ELSE p_operace
    END
$function$;
