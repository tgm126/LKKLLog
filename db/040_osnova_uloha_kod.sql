-- 040: Osnova a úloha bez opakování označení (rozhodnuto 9. 10. 2026; CLAUDE.md bod 10 –
-- evidenční číselník: kod = oficiální označení, zobrazuje se). Dosud: osnova IU / „IU – Výcvik
-- SPL…“, úloha IU_8P / „IU/8P Přezkoušení…“. Nově: osnova IU / „Výcvik SPL…“, úloha 8P
-- (jedinečný v osnově) / „Přezkoušení…“; texty pro aplikaci skládají pohledy (popis,
-- oznaceni). Převod z názvů (týká se i dat z 019_data): osnova bez „IU – “, úloha z „IU/8P …“
-- vezme kód za lomítkem. Školka (S) má v názvech „I/4 …“ – kód 4, zobrazí se „S/4“.

-- --- osnova -----------------------------------------------------------------------------------
UPDATE lkkl.lov_osnova SET nazev = regexp_replace(nazev, '^' || kod || '[[:space:]]*[–-][[:space:]]*', '')
WHERE nazev ~ ('^' || kod || '[[:space:]]*[–-][[:space:]]*[^[:space:]]');

-- --- úloha: kód jedinečný v osnově -------------------------------------------------------------
ALTER TABLE lkkl.lov_uloha DROP CONSTRAINT lov_uloha_kod_key;
UPDATE lkkl.lov_uloha
SET kod = upper(substring(nazev FROM '^[^/[:space:]]+/([^[:space:]]+)')),
    nazev = substring(nazev FROM '^[^/[:space:]]+/[^[:space:]]+[[:space:]]+(.*)$')
WHERE nazev ~ '^[^/[:space:]]+/[^[:space:]]+[[:space:]]+[^[:space:]]';
ALTER TABLE lkkl.lov_uloha ADD CONSTRAINT lov_uloha_osnova_kod UNIQUE (osnova_id, kod);

COMMENT ON COLUMN lkkl.lov_osnova.kod IS 'Oficiální označení osnovy (IU, IA, II…) – zobrazuje se.';
COMMENT ON COLUMN lkkl.lov_uloha.kod IS 'Označení úlohy v osnově (4, 8P…) – zobrazuje se jako IU/8P.';

-- --- pohledy: texty pro aplikaci (sloupce na konci) --------------------------------------------
CREATE OR REPLACE VIEW lkkl.v_lov_osnova AS
SELECT id, kod, nazev, poradi, kategorie_id, kod || ' – ' || nazev AS popis
FROM lkkl.lov_osnova
WHERE platny
ORDER BY poradi, nazev;
COMMENT ON VIEW lkkl.v_lov_osnova IS 'Nabídka: platné osnovy; popis = „IU – Výcvik SPL…“.';

CREATE OR REPLACE VIEW lkkl.v_lov_uloha AS
SELECT u.id, u.kod, u.nazev, u.poradi, u.osnova_id,
       o.kod || '/' || u.kod AS oznaceni,
       o.kod || '/' || u.kod || ' ' || u.nazev AS popis
FROM lkkl.lov_uloha u
JOIN lkkl.lov_osnova o ON o.id = u.osnova_id
WHERE u.platny
ORDER BY u.poradi, u.nazev;
COMMENT ON VIEW lkkl.v_lov_uloha IS 'Nabídka: platné úlohy; oznaceni = „IU/8P“, popis = „IU/8P Přezkoušení…“.';

CREATE OR REPLACE VIEW lkkl.v_uloha_nabidka AS
SELECT u.id, u.nazev, u.poradi, o.id AS osnova_id, o.nazev AS osnova, o.poradi AS osnova_poradi,
       uu.ucel_id, o.kategorie_id,
       o.kod || '/' || u.kod AS oznaceni,
       o.kod || '/' || u.kod || ' ' || u.nazev AS popis,
       o.kod || ' – ' || o.nazev AS osnova_popis
FROM lkkl.lov_uloha u
JOIN lkkl.lov_osnova o ON o.id = u.osnova_id
JOIN lkkl.lov_uloha_ucel uu ON uu.uloha_id = u.id
WHERE u.platny AND o.platny
ORDER BY o.poradi, o.nazev, u.poradi, u.nazev;
COMMENT ON VIEW lkkl.v_uloha_nabidka IS
    'Úlohy pro průvodce: filtrovat podle ucel_id a kategorie_id (prázdná = všechny kategorie); '
    'oznaceni „IU/8P“, popis „IU/8P Přezkoušení…“, osnova_popis „IU – Výcvik SPL…“.';

-- v_let: úloha jako popis („IU/8P Přezkoušení…“, dřív celý název) a označení pro štítek pásku
CREATE OR REPLACE VIEW lkkl.v_let AS
 SELECT l.id,
        CASE
            WHEN l.zruseni_duvod_id IS NOT NULL THEN 'ZRUSEN'::text
            WHEN l.cas_vzletu IS NULL THEN 'NAPLANOVAN'::text
            WHEN l.cas_pristani IS NULL THEN 'VE_VZDUCHU'::text
            ELSE 'UKONCEN'::text
        END AS stav,
    (COALESCE(l.cas_vzletu, l.zalozeno) AT TIME ZONE 'UTC'::text)::date AS den,
    l.letadlo_id,
    a.rejstrik,
    t.nazev AS typ,
    k.nazev AS kategorie,
    k.kod AS kategorie_kod,
    a.soukrome,
    l.ucel_id,
    u.nazev AS ucel,
    u.kod AS ucel_kod,
    v.id IS NOT NULL AS je_vlecny,
    v.id AS vleceny_let_id,
    l.vlecny_let_id,
    z.nazev AS zpusob_vzletu,
    z.kod AS zpusob_vzletu_kod,
    COALESCE(lv.kod::text, l.misto_vzletu_popis) AS misto_vzletu,
    COALESCE(lp.kod::text, l.misto_pristani_popis) AS misto_pristani,
    l.cas_vzletu,
    l.cas_pristani,
    l.doba_min,
        CASE
            WHEN l.zruseni_duvod_id IS NOT NULL THEN 0
            ELSE l.doba_min
        END AS doba_uctovana_min,
    l.pocet_pristani,
    COALESCE(l.pob::bigint, ( SELECT count(*) AS count
           FROM lkkl.posadka p
             JOIN lkkl.lov_funkce f ON f.id = p.funkce_id
          WHERE p.let_id = l.id AND f.na_palube))::smallint AS pob,
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
    l.cas_pristani IS NOT NULL AND l.zalozeno > l.cas_pristani AS dodatecne,
    l.zalozil_id,
    l.zalozeno,
    l.verze,
    l.uloha_id,
    (ulo.kod::text || '/' || ul.kod::text || ' ' || ul.nazev::text)::lkkl.nazev AS uloha,
        CASE
            WHEN k.kod::text = 'KLUZAK'::text OR v.id IS NOT NULL THEN 'PLACHTARSKY'::text
            ELSE 'MOTOROVY'::text
        END AS druh_provozu,
    l.cas_vzletu IS NOT NULL AND l.cas_pristani IS NULL AND l.zruseni_duvod_id IS NULL AND a.max_doba_min IS NOT NULL AND (now() - l.cas_vzletu) > (a.max_doba_min::double precision * '00:01:00'::interval) AS prekrocena_doba,
    ulo.kod::text || '/' || ul.kod::text AS uloha_oznaceni
   FROM lkkl.let l
     JOIN lkkl.lov_letadlo a ON a.id = l.letadlo_id
     JOIN lkkl.lov_typ t ON t.id = a.typ_id
     JOIN lkkl.lov_kategorie k ON k.id = t.kategorie_id
     JOIN lkkl.lov_zpusob_vzletu z ON z.id = l.zpusob_vzletu_id
     LEFT JOIN lkkl.lov_ucel u ON u.id = l.ucel_id
     LEFT JOIN lkkl.let v ON v.vlecny_let_id = l.id
     LEFT JOIN lkkl.lov_letiste lv ON lv.id = l.misto_vzletu_id
     LEFT JOIN lkkl.lov_letiste lp ON lp.id = l.misto_pristani_id
     LEFT JOIN lkkl.posadka pic ON pic.let_id = l.id AND pic.funkce_id = (( SELECT lov_funkce.id
           FROM lkkl.lov_funkce
          WHERE lov_funkce.kod::text = 'PIC'::text))
     LEFT JOIN lkkl.lov_osoba po ON po.id = pic.osoba_id
     LEFT JOIN lkkl.lov_osoba pl ON pl.id = l.platce_id
     LEFT JOIN lkkl.lov_duvod_zruseni dz ON dz.id = l.zruseni_duvod_id
     LEFT JOIN lkkl.lov_uloha ul ON ul.id = l.uloha_id
     LEFT JOIN lkkl.lov_osnova ulo ON ulo.id = ul.osnova_id;

-- historie letu: úloha čitelně („IU/8P Přezkoušení…“)
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
