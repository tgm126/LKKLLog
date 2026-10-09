-- 044: Souhrn dne – počet startů navijákem (zadání 9. 10. 2026: deska, patička plachtařského
-- provozu). Jako ostatní hodnoty souhrnu jen ukončené lety; sloupec na konci pohledu.
CREATE OR REPLACE VIEW lkkl.v_souhrn_dne AS
SELECT den, druh_provozu, letadlo_id, rejstrik, je_vlecny,
       count(*)::integer AS lety,
       sum(pocet_pristani)::integer AS pristani,
       sum(doba_uctovana_min)::integer AS minut,
       (count(*) FILTER (WHERE zpusob_vzletu_kod = 'NAVIJAK'))::integer AS navijaky
FROM lkkl.v_let
WHERE stav = 'UKONCEN'
GROUP BY den, druh_provozu, letadlo_id, rejstrik, je_vlecny;

COMMENT ON VIEW lkkl.v_souhrn_dne IS
    'Souhrn dne: ukončené lety po druhu provozu a letadle (vlečná ve vleku zvlášť, je_vlecny) – '
    'počet letů, přistání, účtovaných minut a startů navijákem. Den = UTC datum vzletu (jako v_let).';
