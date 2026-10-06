-- 016 data: TESTOVACÍ osnovy a úlohy (5. 10. 2026) – uživatel je nahradí skutečnými.

INSERT INTO lkkl.lov_osnova (kod, nazev, poradi, kategorie_id)
SELECT v.kod, v.nazev, v.poradi, k.id
FROM (VALUES
    ('OBECNE', 'Obecné', 10, NULL),
    ('KL_ZAKLADNI', 'Základní výcvik', 20, 'KLUZAK'),
    ('KL_POKRACOVACI', 'Pokračovací výcvik', 30, 'KLUZAK'),
    ('KL_SPORTOVNI', 'Sportovní výcvik', 40, 'KLUZAK'),
    ('LET_PPL', 'Výcvik PPL(A)', 50, 'LETOUN'),
    ('PREZKOUSENI', 'Přezkoušení', 60, NULL)
) AS v(kod, nazev, poradi, kategorie)
LEFT JOIN lkkl.lov_kategorie k ON k.kod = v.kategorie;

INSERT INTO lkkl.lov_uloha (kod, nazev, poradi, osnova_id)
SELECT v.kod, v.nazev, v.poradi, o.id
FROM (VALUES
    ('OBECNE_PROSTOR', 'Let do prostoru', 10, 'OBECNE'),
    ('OBECNE_OKRUHY', 'Okruhy', 20, 'OBECNE'),
    ('OBECNE_NAVIGACE', 'Navigační let', 30, 'OBECNE'),
    ('KL_A1', 'A1 – Seznamovací let', 10, 'KL_ZAKLADNI'),
    ('KL_A5', 'A5 – Zatáčky', 20, 'KL_ZAKLADNI'),
    ('KL_B3', 'B3 – Okruhy', 30, 'KL_ZAKLADNI'),
    ('KL_B10', 'B10 – První sólo', 40, 'KL_ZAKLADNI'),
    ('KL_C1', 'C1 – Let ve stoupavých proudech', 10, 'KL_POKRACOVACI'),
    ('KL_C4', 'C4 – Přistání do terénu', 20, 'KL_POKRACOVACI'),
    ('KL_S1', 'S1 – Přelet 50 km', 10, 'KL_SPORTOVNI'),
    ('LET_L1', 'L1 – Seznamovací let', 10, 'LET_PPL'),
    ('LET_L4', 'L4 – Okruhy', 20, 'LET_PPL'),
    ('LET_L9', 'L9 – Navigační let', 30, 'LET_PPL'),
    ('PR_ODBORNA', 'Přezkoušení odborné způsobilosti', 10, 'PREZKOUSENI'),
    ('PR_TYP', 'Přezkoušení na typ', 20, 'PREZKOUSENI')
) AS v(kod, nazev, poradi, osnova)
JOIN lkkl.lov_osnova o ON o.kod = v.osnova;

-- Kde se osnovy nabízejí: obecné u normálního letu; výcvikové u výcviku, sóla i normálního letu;
-- přezkoušení u přezkoušení.
INSERT INTO lkkl.osnova_ucel (osnova_id, ucel_id)
SELECT o.id, u.id
FROM (VALUES
    ('OBECNE', 'NORMALNI'),
    ('KL_ZAKLADNI', 'VYCVIK'), ('KL_ZAKLADNI', 'VYCVIK_SOLO'), ('KL_ZAKLADNI', 'NORMALNI'),
    ('KL_POKRACOVACI', 'VYCVIK'), ('KL_POKRACOVACI', 'VYCVIK_SOLO'), ('KL_POKRACOVACI', 'NORMALNI'),
    ('KL_SPORTOVNI', 'VYCVIK'), ('KL_SPORTOVNI', 'VYCVIK_SOLO'), ('KL_SPORTOVNI', 'NORMALNI'),
    ('LET_PPL', 'VYCVIK'), ('LET_PPL', 'VYCVIK_SOLO'), ('LET_PPL', 'NORMALNI'),
    ('PREZKOUSENI', 'PREZKOUSENI')
) AS v(osnova, ucel)
JOIN lkkl.lov_osnova o ON o.kod = v.osnova
JOIN lkkl.lov_ucel u ON u.kod = v.ucel;
