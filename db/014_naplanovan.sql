-- 014: let bez vzletu se jmenuje „naplánovaný“ (dřív „připravený“) – kód stavu NAPLANOVAN.
-- Nabídka letadel ukazuje i letadla mimo provoz (průvodce je zobrazí jinou barvou a nedovolí
-- vybrat).

COMMENT ON TABLE lkkl.let IS 'Let. Stav se odvodí (v_let): bez vzletu = naplánovaný, vzlet bez přistání = ve vzduchu, obojí = ukončený, důvod zrušení = zrušený.';

CREATE OR REPLACE VIEW lkkl.v_let AS
SELECT l.id,
       CASE WHEN l.zruseni_duvod_id IS NOT NULL THEN 'ZRUSEN'
            WHEN l.cas_vzletu IS NULL THEN 'NAPLANOVAN'
            WHEN l.cas_pristani IS NULL THEN 'VE_VZDUCHU'
            ELSE 'UKONCEN' END                              AS stav,
       (coalesce(l.cas_vzletu, l.zalozeno) AT TIME ZONE 'UTC')::date AS den,
       l.letadlo_id, a.rejstrik, t.nazev AS typ, k.nazev AS kategorie, k.kod AS kategorie_kod,
       a.soukrome,
       l.ucel_id, u.nazev AS ucel, u.kod AS ucel_kod,
       v.id IS NOT NULL                                    AS je_vlecny,
       v.id                                                AS vleceny_let_id,
       l.vlecny_let_id,
       z.nazev AS zpusob_vzletu, z.kod AS zpusob_vzletu_kod,
       coalesce(lv.kod, l.misto_vzletu_popis)              AS misto_vzletu,
       coalesce(lp.kod, l.misto_pristani_popis)            AS misto_pristani,
       l.cas_vzletu, l.cas_pristani, l.doba_min,
       CASE WHEN l.zruseni_duvod_id IS NOT NULL OR l.doba_nulova THEN 0
            ELSE l.doba_min END                            AS doba_uctovana_min,
       l.pocet_pristani,
       coalesce(l.pob, (SELECT count(*) FROM lkkl.posadka p JOIN lkkl.lov_funkce f ON f.id = p.funkce_id
                        WHERE p.let_id = l.id AND f.na_palube))::smallint AS pob,
       pic.osoba_id AS pic_id, po.jmeno AS pic_jmeno, po.prijmeni AS pic_prijmeni,
       l.platce_id, l.plati_aeroklub, pl.jmeno AS platce_jmeno, pl.prijmeni AS platce_prijmeni,
       l.poznamka,
       l.zruseni_duvod_id, dz.nazev AS duvod_zruseni, l.zruseno,
       l.cas_pristani IS NOT NULL AND l.zalozeno > l.cas_pristani AS dodatecne,
       l.zalozil_id, l.zalozeno, l.verze
FROM lkkl.let l
JOIN lkkl.letadlo a                ON a.id = l.letadlo_id
JOIN lkkl.lov_typ t                ON t.id = a.typ_id
JOIN lkkl.lov_kategorie k          ON k.id = t.kategorie_id
JOIN lkkl.lov_zpusob_vzletu z      ON z.id = l.zpusob_vzletu_id
LEFT JOIN lkkl.lov_ucel u          ON u.id = l.ucel_id
LEFT JOIN lkkl.let v               ON v.vlecny_let_id = l.id
LEFT JOIN lkkl.lov_letiste lv      ON lv.id = l.misto_vzletu_id
LEFT JOIN lkkl.lov_letiste lp      ON lp.id = l.misto_pristani_id
LEFT JOIN lkkl.posadka pic         ON pic.let_id = l.id
                                  AND pic.funkce_id = (SELECT id FROM lkkl.lov_funkce WHERE kod = 'PIC')
LEFT JOIN lkkl.osoba po            ON po.id = pic.osoba_id
LEFT JOIN lkkl.osoba pl            ON pl.id = l.platce_id
LEFT JOIN lkkl.lov_duvod_zruseni dz ON dz.id = l.zruseni_duvod_id;

CREATE OR REPLACE VIEW lkkl.v_letadlo_nabidka AS
SELECT l.id,
       l.rejstrik,
       t.nazev AS typ,
       k.nazev AS kategorie,
       k.kod   AS kategorie_kod,
       l.vlecne,
       l.soukrome,
       l.mimo_provoz
FROM lkkl.letadlo l
JOIN lkkl.lov_typ t       ON t.id = l.typ_id
JOIN lkkl.lov_kategorie k ON k.id = t.kategorie_id
ORDER BY k.poradi, t.poradi, t.nazev, l.rejstrik;
COMMENT ON VIEW lkkl.v_letadlo_nabidka IS 'Nabídka letadel pro nový let ve stálém pořadí; letadla mimo provoz jsou vidět, ale nejdou vybrat.';
