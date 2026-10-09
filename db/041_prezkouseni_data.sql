-- 041 data: typy přezkoušení a kdo je smí provést – počáteční naplnění pro novou databázi, kde
-- se kategorie letadel (001 data) a oprávnění instruktorů a examinátorů (021 data) zakládají až
-- po skriptech struktury. Na serveru totéž udělala migrace 041 (data už existovala); dál typy
-- zadává a mění uživatel v databázi (kontrola: v_osoba_prezkouseni). Jde spustit opakovaně.
-- Pro novou databázi (po všech skriptech struktury, po 001 a 021 data):
--   psql -1 -f db/041_prezkouseni_data.sql

INSERT INTO lkkl.lov_prezkouseni (kod, nazev, poradi, platny, kategorie_id)
SELECT v.kod, v.nazev, v.poradi, true, k.id
FROM (VALUES
    ('ST-SPL',      'Zkouška dovednosti SPL',                                      10, 'KLUZAK'),
    ('PC-SPL',      'Přezkoušení odborné způsobilosti SPL',                        20, 'KLUZAK'),
    ('PC-CLOUD',    'Přezkoušení pro lety v oblacích',                             30, 'KLUZAK'),
    ('AOC-FI-S',    'Ověření způsobilosti instruktora FI(S)',                      40, 'KLUZAK'),
    ('ST-TMG',      'Zkouška dovednosti TMG',                                      50, 'TMG'),
    ('PC-TMG',      'Přezkoušení odborné způsobilosti TMG',                        60, 'TMG'),
    ('ST-LAPL-A',   'Zkouška dovednosti LAPL(A)',                                  70, 'LETOUN'),
    ('ST-PPL-A',    'Zkouška dovednosti PPL(A)',                                   80, 'LETOUN'),
    ('PC-LAPL-A',   'Přezkoušení odborné způsobilosti LAPL(A)',                    90, 'LETOUN'),
    ('PC-SEP',      'Přezkoušení odborné způsobilosti SEP (prodloužení, obnova)', 100, 'LETOUN'),
    ('AOC-FI-A',    'Ověření způsobilosti instruktora FI(A), CRI(A)',             110, 'LETOUN'),
    ('ST-ULL',      'Závěrečná zkouška pilota ULL',                               120, 'UL'),
    ('PC-ULL',      'Ověření praktických dovedností pilota ULL',                  130, 'UL'),
    ('ST-ULL-CTR',  'Zkouška pro řízené lety VFR',                                140, 'UL'),
    ('ST-ULL-VLEK', 'Zkouška kvalifikace vlekař ULL',                             150, 'UL'),
    ('AOC-ULLI',    'Přezkoušení instruktora ULL',                                160, 'UL')
) AS v(kod, nazev, poradi, kategorie)
JOIN lkkl.lov_kategorie k ON k.kod = v.kategorie
ON CONFLICT (kod) DO NOTHING;

-- kategorie nových oprávnění (oprávnění založila migrace 041)
INSERT INTO lkkl.lov_opravneni_kategorie (opravneni_id, kategorie_id)
SELECT o.id, k.id
FROM (VALUES ('FIE_A', 'LETOUN'), ('FIE_A', 'TMG'), ('FE_S_FI', 'KLUZAK'), ('FE_S_FI', 'TMG'))
     AS v(opravneni, kategorie)
JOIN lkkl.lov_opravneni o ON o.kod = v.opravneni
JOIN lkkl.lov_kategorie k ON k.kod = v.kategorie
ON CONFLICT DO NOTHING;

INSERT INTO lkkl.lov_prezkouseni_opravneni (prezkouseni_id, opravneni_id)
SELECT p.id, o.id
FROM (VALUES
    ('ST-SPL', 'FE_S'), ('PC-SPL', 'FE_S'), ('PC-CLOUD', 'FE_S'), ('AOC-FI-S', 'FE_S_FI'),
    ('ST-TMG', 'FE_S'), ('ST-TMG', 'FE_A'),
    ('PC-TMG', 'FE_S'), ('PC-TMG', 'FE_A'), ('PC-TMG', 'CRE_A'),
    ('ST-LAPL-A', 'FE_A'), ('ST-PPL-A', 'FE_A'), ('PC-LAPL-A', 'FE_A'),
    ('PC-SEP', 'FE_A'), ('PC-SEP', 'CRE_A'), ('AOC-FI-A', 'FIE_A'),
    ('ST-ULL', 'INSPEKTOR_ULL'), ('PC-ULL', 'INSPEKTOR_ULL'), ('ST-ULL-CTR', 'INSPEKTOR_ULL'),
    ('ST-ULL-VLEK', 'INSPEKTOR_ULL'), ('AOC-ULLI', 'INSPEKTOR_ULL')
) AS v(prezkouseni, opravneni)
JOIN lkkl.lov_prezkouseni p ON p.kod = v.prezkouseni
JOIN lkkl.lov_opravneni o ON o.kod = v.opravneni
ON CONFLICT DO NOTHING;
