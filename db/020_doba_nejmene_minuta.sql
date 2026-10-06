-- 020: doba letu se zapisuje nejméně jako 1 minuta; „start bez doby“ (doba_nulova) se ruší.
--
-- Let změřený pod minutu obrazovka nabídne zrušit (přerušený vzlet), nebo počítat – pak
-- s dobou 1 minuta. Přepínač „start bez doby“ (0 minut, start se počítá) tím zaniká.
-- Na serveru ho žádný let nepoužívá.

DROP VIEW lkkl.v_let;

ALTER TABLE lkkl.let DROP CONSTRAINT doba_nulova_jen_kratky;
ALTER TABLE lkkl.let DROP COLUMN doba_nulova;
DELETE FROM lkkl.lov_audit_popisek WHERE tabulka = 'let' AND sloupec = 'doba_nulova';

ALTER TABLE lkkl.let ALTER COLUMN doba_min SET EXPRESSION AS (
    CASE WHEN cas_pristani IS NOT NULL
         THEN greatest(1, floor((extract(epoch FROM cas_pristani - cas_vzletu) + 30) / 60))::integer
    END
);
COMMENT ON COLUMN lkkl.let.doba_min IS
    'Doba letu v celých minutách (30 s a víc nahoru), nejméně 1 minuta – počítá databáze.';

CREATE VIEW lkkl.v_let AS
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
    ul.nazev AS uloha
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
    'Lety s odvozeným stavem, dnem (UTC datum vzletu), vlekem, účtovanou dobou a příznakem „dodatečně“.';
