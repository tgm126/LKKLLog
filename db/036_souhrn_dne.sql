-- 036: Výpočty z aplikace do databáze, 2. část (revize 8. 10. 2026, body 6 a 8).
-- 6. v_souhrn_dne: ukončené lety dne po druhu provozu a letadle (vlečná ve vleku zvlášť) –
--    lety, přistání, účtované minuty. Dosud počítal frontend z pásků; souhrny desky ho teď
--    jen vykreslí (součty v patičce sečte z řádků). Poslouží i uzávěrce a účetnictví.
-- 8. v_let.prekrocena_doba: let ve vzduchu déle, než je maximální doba letadla (dosud Python).
--    Text varování (i „po konci soumraku“ – sluneční časy počítá aplikace) skládá server.

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
    ul.nazev AS uloha,
        CASE
            WHEN k.kod::text = 'KLUZAK'::text OR v.id IS NOT NULL THEN 'PLACHTARSKY'::text
            ELSE 'MOTOROVY'::text
        END AS druh_provozu,
    l.cas_vzletu IS NOT NULL AND l.cas_pristani IS NULL AND l.zruseni_duvod_id IS NULL
      AND a.max_doba_min IS NOT NULL
      AND now() - l.cas_vzletu > a.max_doba_min * '00:01:00'::interval AS prekrocena_doba
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
     LEFT JOIN lkkl.lov_uloha ul ON ul.id = l.uloha_id;

COMMENT ON VIEW lkkl.v_let IS
    'Lety s odvozeným stavem, dnem (UTC datum vzletu), vlekem, účtovanou dobou, příznakem '
    '„dodatečně“, druhem provozu (PLACHTARSKY = kluzák a vlečný let, MOTOROVY = ostatní) '
    'a příznakem překročené maximální doby letu (jen ve vzduchu, podle now()).';

CREATE VIEW lkkl.v_souhrn_dne AS
SELECT den, druh_provozu, letadlo_id, rejstrik, je_vlecny,
       count(*)::integer AS lety,
       sum(pocet_pristani)::integer AS pristani,
       sum(doba_uctovana_min)::integer AS minut
FROM lkkl.v_let
WHERE stav = 'UKONCEN'
GROUP BY den, druh_provozu, letadlo_id, rejstrik, je_vlecny;

COMMENT ON VIEW lkkl.v_souhrn_dne IS
    'Souhrn dne: ukončené lety po druhu provozu a letadle (vlečná ve vleku zvlášť, je_vlecny) – '
    'počet letů, přistání a účtovaných minut. Den = UTC datum vzletu (jako v_let).';
