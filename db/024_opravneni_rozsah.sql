-- 024: oprávnění osob podle kategorií letadel, role v letu jako číselník, omezení u osoby
-- (návrh docs/navrh-opravneni.md, srovnání docs/srovnani-opravneni.md). Slouží jen k nabídkám
-- osob v posádce; nic se nekontroluje ani neblokuje.
--   lov_role                      – role v letu (instruktor, dozor, examinátor, vlekař) = účel + funkce
--   lov_opravneni_role            – oprávnění → role (místo účel + funkce u každého oprávnění)
--   lov_opravneni_kategorie       – pro které kategorie se oprávnění smí vydat (bez řádku = žádná)
--   lov_osoba_opravneni.omezene   – instruktor pod dohledem (místo druhů FI_S_OMEZENY, FI_A_OMEZENY)
--   lov_osoba_opravneni_kategorie – pro které kategorie osoba oprávnění má
-- Stávající data se převedou beze ztráty: osoba dostane oprávnění pro všechny povolené
-- kategorie (= dosavadní chování), správce pak odškrtá, co nemá.

DROP VIEW lkkl.v_osoba_smi;
DROP VIEW lkkl.v_osoba_opravneni;
DROP VIEW lkkl.v_lov_opravneni;

-- --- role v letu ------------------------------------------------------------------------------
CREATE TABLE lkkl.lov_role (
    id        bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    kod       lkkl.kod    NOT NULL UNIQUE,
    nazev     lkkl.nazev  NOT NULL,
    poradi    lkkl.poradi NOT NULL,
    platny    lkkl.platny NOT NULL,
    ucel_id   bigint      REFERENCES lkkl.lov_ucel,
    funkce_id bigint      NOT NULL REFERENCES lkkl.lov_funkce,
    UNIQUE NULLS NOT DISTINCT (ucel_id, funkce_id)
);
COMMENT ON TABLE lkkl.lov_role IS 'Role v letu, do které se nabízejí osoby podle oprávnění: kde v letu sedí (účel + funkce). Kódy používá program.';
COMMENT ON COLUMN lkkl.lov_role.ucel_id IS 'Účel letu; prázdný = vlečný let (jako let.ucel_id).';
CREATE INDEX lov_role_funkce ON lkkl.lov_role (funkce_id);

INSERT INTO lkkl.lov_role (kod, nazev, poradi, ucel_id, funkce_id)
SELECT v.kod, v.nazev, v.poradi, u.id, f.id
FROM (VALUES
    ('INSTRUKTOR', 'Instruktor', 10, 'VYCVIK',      'PIC'),
    ('DOZOR',      'Dozor',      20, 'VYCVIK_SOLO', 'DOZOR'),
    ('EXAMINATOR', 'Examinátor', 30, 'PREZKOUSENI', 'PIC'),
    ('VLEKAR',     'Vlekař',     40, NULL,          'PIC')
) AS v(kod, nazev, poradi, ucel, funkce)
LEFT JOIN lkkl.lov_ucel u ON u.kod = v.ucel
JOIN lkkl.lov_funkce f    ON f.kod = v.funkce;

-- --- oprávnění → role ---------------------------------------------------------------------------
ALTER TABLE lkkl.lov_opravneni_role ADD COLUMN role_id bigint REFERENCES lkkl.lov_role;
UPDATE lkkl.lov_opravneni_role orl SET role_id = r.id
FROM lkkl.lov_role r
WHERE r.funkce_id = orl.funkce_id AND r.ucel_id IS NOT DISTINCT FROM orl.ucel_id;
DELETE FROM lkkl.lov_opravneni_role WHERE role_id IS NULL;  -- místo v letu, které není rolí
ALTER TABLE lkkl.lov_opravneni_role
    DROP COLUMN id,
    DROP COLUMN ucel_id,
    DROP COLUMN funkce_id,
    ALTER COLUMN role_id SET NOT NULL,
    ADD PRIMARY KEY (opravneni_id, role_id);
COMMENT ON TABLE lkkl.lov_opravneni_role IS 'K jakým rolím v letu oprávnění opravňuje – nabídka osob v posádce.';
CREATE INDEX lov_opravneni_role_role ON lkkl.lov_opravneni_role (role_id);

-- Dohoda 7. 10. 2026 (docs/podklady/prezkouseni.md): přezkoušení jen examinátorům, výcvik
-- a dozor jen instruktorům (examinátor je zpravidla i instruktor a roli má z toho oprávnění).
DELETE FROM lkkl.lov_opravneni_role orl
USING lkkl.lov_opravneni o, lkkl.lov_role r
WHERE o.id = orl.opravneni_id AND r.id = orl.role_id
  AND ((r.kod = 'EXAMINATOR' AND o.kod IN ('FI_S', 'FI_A', 'CRI_A', 'INSTRUKTOR_ULL'))
    OR (r.kod IN ('INSTRUKTOR', 'DOZOR') AND o.kod IN ('FE_S', 'FE_A', 'CRE_A', 'INSPEKTOR_ULL')));

-- --- omezení je vlastnost oprávnění osoby -------------------------------------------------------
ALTER TABLE lkkl.lov_osoba_opravneni ADD COLUMN omezene boolean NOT NULL DEFAULT false;
COMMENT ON COLUMN lkkl.lov_osoba_opravneni.omezene IS 'Instruktor s omezením (vyučuje pod dohledem, nesmí povolit první sólo) – jen evidence, nabídku neovlivní.';

-- Osoby s druhem „… omezený“ dostanou základní oprávnění s omezením (kdo má obojí, má neomezené).
INSERT INTO lkkl.lov_osoba_opravneni (osoba_id, opravneni_id, omezene)
SELECT oo.osoba_id, z.id, true
FROM lkkl.lov_osoba_opravneni oo
JOIN lkkl.lov_opravneni o ON o.id = oo.opravneni_id AND o.omezene
JOIN lkkl.lov_opravneni z ON z.kod = replace(o.kod, '_OMEZENY', '')
ON CONFLICT (osoba_id, opravneni_id) DO NOTHING;
DELETE FROM lkkl.lov_osoba_opravneni oo USING lkkl.lov_opravneni o
WHERE o.id = oo.opravneni_id AND o.omezene;
DELETE FROM lkkl.lov_opravneni_role orl USING lkkl.lov_opravneni o
WHERE o.id = orl.opravneni_id AND o.omezene;
DELETE FROM lkkl.lov_opravneni_kategorie ok USING lkkl.lov_opravneni o
WHERE o.id = ok.opravneni_id AND o.omezene;
DELETE FROM lkkl.lov_opravneni WHERE omezene;
ALTER TABLE lkkl.lov_opravneni DROP COLUMN omezene;

-- --- kategorie: co se smí vydat × co osoba má ---------------------------------------------------
COMMENT ON TABLE lkkl.lov_opravneni_kategorie IS 'Pro které kategorie letadel se oprávnění smí vydat; bez řádku pro žádnou.';
-- Vlekař dosud „bez kategorie = všechna letadla“; vleká se letouny a UL (TMG v klubu ne).
INSERT INTO lkkl.lov_opravneni_kategorie (opravneni_id, kategorie_id)
SELECT o.id, k.id
FROM lkkl.lov_opravneni o
JOIN lkkl.lov_kategorie k ON k.kod IN ('LETOUN', 'UL')
WHERE o.kod = 'VLEKAR'
ON CONFLICT DO NOTHING;

CREATE TABLE lkkl.lov_osoba_opravneni_kategorie (
    osoba_id     bigint NOT NULL,
    opravneni_id bigint NOT NULL,
    kategorie_id bigint NOT NULL,
    PRIMARY KEY (osoba_id, opravneni_id, kategorie_id),
    CONSTRAINT opravneni_osoby FOREIGN KEY (osoba_id, opravneni_id)
        REFERENCES lkkl.lov_osoba_opravneni,
    CONSTRAINT kategorie_povolena FOREIGN KEY (opravneni_id, kategorie_id)
        REFERENCES lkkl.lov_opravneni_kategorie
);
COMMENT ON TABLE lkkl.lov_osoba_opravneni_kategorie IS 'Pro které kategorie letadel osoba oprávnění má (jen z povolených u oprávnění).';
CREATE INDEX lov_osoba_opravneni_kategorie_rozsah ON lkkl.lov_osoba_opravneni_kategorie (opravneni_id, kategorie_id);

INSERT INTO lkkl.lov_osoba_opravneni_kategorie (osoba_id, opravneni_id, kategorie_id)
SELECT oo.osoba_id, oo.opravneni_id, ok.kategorie_id
FROM lkkl.lov_osoba_opravneni oo
JOIN lkkl.lov_opravneni_kategorie ok ON ok.opravneni_id = oo.opravneni_id;

-- --- pohledy ------------------------------------------------------------------------------------
CREATE VIEW lkkl.v_lov_opravneni AS
SELECT * FROM lkkl.lov_opravneni WHERE platny ORDER BY poradi, nazev;

CREATE VIEW lkkl.v_osoba_smi AS
SELECT DISTINCT oo.osoba_id, r.kod AS role_kod, u.kod AS ucel_kod, f.kod AS funkce_kod,
       k.kod AS kategorie_kod
FROM lkkl.lov_osoba_opravneni oo
JOIN lkkl.lov_opravneni o                  ON o.id = oo.opravneni_id AND o.platny
JOIN lkkl.lov_osoba_opravneni_kategorie ok ON ok.osoba_id = oo.osoba_id
                                          AND ok.opravneni_id = oo.opravneni_id
JOIN lkkl.lov_kategorie k                  ON k.id = ok.kategorie_id
JOIN lkkl.lov_opravneni_role orl           ON orl.opravneni_id = oo.opravneni_id
JOIN lkkl.lov_role r                       ON r.id = orl.role_id AND r.platny
LEFT JOIN lkkl.lov_ucel u                  ON u.id = r.ucel_id
JOIN lkkl.lov_funkce f                     ON f.id = r.funkce_id;
COMMENT ON VIEW lkkl.v_osoba_smi IS 'Role, které osoba smí zastat: role, účel (prázdný = vlečný let), funkce a kategorie letadla.';

-- Pro kontrolu v databázi: osoby a jejich oprávnění s kategoriemi v jednom řádku.
CREATE VIEW lkkl.v_osoba_opravneni AS
SELECT os.id, os.prijmeni, os.jmeno, os.aktivni,
       string_agg(o.nazev || ' (' || coalesce(ok.kategorie, '–')
                  || CASE WHEN oo.omezene THEN '; omezené' ELSE '' END || ')',
                  ', ' ORDER BY o.poradi) AS opravneni
FROM lkkl.lov_osoba os
LEFT JOIN lkkl.lov_osoba_opravneni oo ON oo.osoba_id = os.id
LEFT JOIN lkkl.lov_opravneni o        ON o.id = oo.opravneni_id
LEFT JOIN LATERAL (
    SELECT string_agg(k.nazev, ', ' ORDER BY k.poradi) AS kategorie
    FROM lkkl.lov_osoba_opravneni_kategorie x
    JOIN lkkl.lov_kategorie k ON k.id = x.kategorie_id
    WHERE x.osoba_id = oo.osoba_id AND x.opravneni_id = oo.opravneni_id
) ok ON true
GROUP BY os.id
ORDER BY os.prijmeni, os.jmeno;
COMMENT ON VIEW lkkl.v_osoba_opravneni IS 'Přehled oprávnění osob s kategoriemi a omezením (kontrola zadání).';

-- --- audit --------------------------------------------------------------------------------------
-- Převod výše se do historie nezapisuje (trigger až po naplnění).
CREATE TRIGGER audit AFTER INSERT OR UPDATE OR DELETE ON lkkl.lov_osoba_opravneni_kategorie
    FOR EACH ROW EXECUTE FUNCTION lkkl.audit_zapsat();
INSERT INTO lkkl.lov_audit_popisek (tabulka, sloupec, popisek, poradi) VALUES
    ('lov_osoba_opravneni', 'omezene', 'omezené', 30),
    ('lov_osoba_opravneni_kategorie', 'opravneni_id', 'oprávnění', 10),
    ('lov_osoba_opravneni_kategorie', 'kategorie_id', 'kategorie', 20);

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
