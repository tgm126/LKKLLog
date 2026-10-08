-- 037: Poloha letadla jako výchozí místo vzletu (rozhodnuto 8. 10. 2026). Poloha = poslední
-- evidované přistání (035) – nový let s letadlem má výchozí místo vzletu tam; formulář
-- potřebuje vědět, zda jde o letiště (id), nebo o místo v terénu (popis). Sloupce na konci.

CREATE OR REPLACE VIEW lkkl.v_lov_letadlo AS
SELECT l.id, l.rejstrik, t.nazev AS typ, k.nazev AS kategorie, k.kod AS kategorie_kod,
       t.pocet_mist, l.max_doba_min, l.vlecne, l.soukrome, l.mimo_provoz,
       coalesce(p.kod::text, p.misto_pristani_popis) AS poloha,
       p.misto_pristani_id AS poloha_letiste_id,
       p.misto_pristani_popis AS poloha_popis
FROM lkkl.lov_letadlo l
JOIN lkkl.lov_typ t ON t.id = l.typ_id
JOIN lkkl.lov_kategorie k ON k.id = t.kategorie_id
LEFT JOIN LATERAL (
    SELECT x.misto_pristani_id, x.misto_pristani_popis, lp.kod
    FROM lkkl.let x LEFT JOIN lkkl.lov_letiste lp ON lp.id = x.misto_pristani_id
    WHERE x.letadlo_id = l.id AND x.cas_pristani IS NOT NULL AND x.zruseni_duvod_id IS NULL
    ORDER BY x.cas_pristani DESC LIMIT 1
) p ON true
WHERE l.platny
ORDER BY k.poradi, t.poradi, t.nazev, l.rejstrik;

COMMENT ON VIEW lkkl.v_lov_letadlo IS
    'Platná letadla pro nabídky a obrazovky: typ, kategorie, počet míst, poloha (poslední '
    'evidované přistání – kód nebo popis, a zvlášť id letiště / popis: výchozí místo vzletu '
    'nového letu); i mimo provoz (zobrazí se, nejdou vybrat). Vyřazená se neukazují.';
