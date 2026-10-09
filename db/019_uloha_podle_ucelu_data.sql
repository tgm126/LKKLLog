-- 019 data: osnovy výcviku na kluzácích podle dokumentu „Program výcviku na kluzácích“
-- (AeČR, v.6 z 1. 8. 2021, úprava AK Kladno). Jen letová cvičení (pozemní přípravy se
-- k letu nenabízejí); označení je v kódu (osnova IU, úloha 4 → „IU/4“ skládá pohled – 040). Cvičení II/10–12 (na TMG; poslední
-- řádek osnovy II v dokumentu nemá číslo – je to 12). Nahrazuje testovací osnovy ze 016.
--
-- Vazba úloha ↔ účel podle sloupců „dvojí“ a „samostatně“ v osnovách:
--   výcvik = dvojí řízení s FI(S), sólo = samostatně pod dozorem (žák), normální = držitel SPL,
--   přezkoušení = II/9P (obnova CLOUD s FE).

-- Testovací osnovy a úlohy (žádný let je nepoužívá; jinak skript skončí chybou a nic nezmění).
DELETE FROM lkkl.lov_uloha_ucel
WHERE uloha_id IN (SELECT u.id FROM lkkl.lov_uloha u JOIN lkkl.lov_osnova o ON o.id = u.osnova_id
                   WHERE o.kod IN ('OBECNE', 'KL_ZAKLADNI', 'KL_POKRACOVACI', 'KL_SPORTOVNI',
                                   'LET_PPL', 'PREZKOUSENI'));
DELETE FROM lkkl.lov_uloha
WHERE osnova_id IN (SELECT id FROM lkkl.lov_osnova
                    WHERE kod IN ('OBECNE', 'KL_ZAKLADNI', 'KL_POKRACOVACI', 'KL_SPORTOVNI',
                                  'LET_PPL', 'PREZKOUSENI'));
DELETE FROM lkkl.lov_osnova
WHERE kod IN ('OBECNE', 'KL_ZAKLADNI', 'KL_POKRACOVACI', 'KL_SPORTOVNI', 'LET_PPL', 'PREZKOUSENI');

INSERT INTO lkkl.lov_osnova (kod, nazev, poradi, platny, kategorie_id)
SELECT v.kod, v.nazev, v.poradi, true, k.id
FROM (VALUES
    ('IU', 'Výcvik SPL (naviják a aerovlek)', 10),
    ('IA', 'Výcvik SPL (aerovlek, samostart)', 20),
    ('II', 'Sportovní výcvik', 30)
) AS v(kod, nazev, poradi)
CROSS JOIN lkkl.lov_kategorie k
WHERE k.kod = 'KLUZAK';

-- Úlohy: osnova, cvičení, krátký název, účely (V = výcvik, S = sólo, N = normální, P = přezkoušení).
CREATE TEMPORARY TABLE nove_ulohy (osnova text, cv text, nazev text, poradi int, ucely text)
ON COMMIT DROP;
INSERT INTO nove_ulohy VALUES
    ('IU', '1',  'Seznamovací let', 10, 'V'),
    ('IU', '2',  'Účinky kormidel, přímý let a zatáčky', 20, 'V'),
    ('IU', '3',  'Pády, skluzy, spirály, mezní rychlosti', 30, 'V'),
    ('IU', '4',  'Navijákové vzlety, okruh a přistání', 40, 'V'),
    ('IU', '5',  'Opravy vadných přistání', 50, 'V'),
    ('IU', '6',  'Mimořádné případy při navijáku, omezený prostor', 60, 'V'),
    ('IU', '7',  'Aerovlek, vývrtky, pády, spirály', 70, 'V'),
    ('IU', '8P', 'Přezkoušení před samostatnými lety', 80, 'V'),
    ('IU', '9',  'První samostatný let', 90, 'S'),
    ('IU', '10', 'Lety po okruhu a do prostoru', 100, 'VS'),
    ('IU', '11', 'Přistání do omezeného prostoru', 110, 'VS'),
    ('IU', '12', 'Využití stoupavých proudů', 120, 'VS'),
    ('IU', '13', 'Traťový navigační let', 130, 'VS'),

    ('IA', '1',  'Seznamovací let', 10, 'V'),
    ('IA', '2',  'Účinky kormidel, přímý let a zatáčky', 20, 'V'),
    ('IA', '3',  'Pády, skluzy, spirály, mezní rychlosti', 30, 'V'),
    ('IA', '4',  'Vzlety aerovlekem / samostartem, okruh a přistání', 40, 'V'),
    ('IA', '5',  'Opravy vadných přistání', 50, 'V'),
    ('IA', '6',  'Mimořádné případy, omezený prostor', 60, 'V'),
    ('IA', '7',  'Aerovlek, vývrtky, pády, spirály', 70, 'V'),
    ('IA', '8P', 'Přezkoušení před samostatnými lety', 80, 'V'),
    ('IA', '9',  'První samostatný let', 90, 'S'),
    ('IA', '10', 'Lety po okruhu a do prostoru', 100, 'VS'),
    ('IA', '11', 'Přistání do omezeného prostoru', 110, 'VS'),
    ('IA', '12', 'Využití stoupavých proudů', 120, 'VS'),
    ('IA', '13', 'Traťový navigační let', 130, 'VS'),

    ('II', '1',  'Termika, svah a lety do prostoru', 10, 'VN'),
    ('II', '2',  'Let po okruhu', 20, 'VN'),
    ('II', '3',  'Přistání do omezeného prostoru', 30, 'VN'),
    ('II', '4',  'Mimořádné případy', 40, 'VN'),
    ('II', '5',  'Navigační let ve dvojím', 50, 'V'),
    ('II', '6',  'Samostatný přelet', 60, 'N'),
    ('II', '7',  'Lety v dlouhé vlně', 70, 'VN'),
    ('II', '8',  'Lety v oblačnosti', 80, 'VN'),
    ('II', '9P', 'Přezkoušení CLOUD', 90, 'P'),
    ('II', '10', 'TMG – vzlet, okruh, přistání', 100, 'VN'),
    ('II', '11', 'TMG – zvláštní případy za letu', 110, 'V'),
    ('II', '12', 'TMG – navigační lety a lety do prostoru', 120, 'VN');

INSERT INTO lkkl.lov_uloha (kod, nazev, poradi, platny, osnova_id)
SELECT n.cv, n.nazev, n.poradi, true, o.id
FROM nove_ulohy n JOIN lkkl.lov_osnova o ON o.kod = n.osnova;

INSERT INTO lkkl.lov_uloha_ucel (uloha_id, ucel_id)
SELECT u.id, uc.id
FROM nove_ulohy n
JOIN lkkl.lov_osnova o ON o.kod = n.osnova
JOIN lkkl.lov_uloha u ON u.osnova_id = o.id AND u.kod = n.cv
CROSS JOIN LATERAL regexp_split_to_table(n.ucely, '') AS z(pismeno)
JOIN lkkl.lov_ucel uc ON uc.kod = CASE z.pismeno
    WHEN 'V' THEN 'VYCVIK' WHEN 'S' THEN 'VYCVIK_SOLO'
    WHEN 'N' THEN 'NORMALNI' WHEN 'P' THEN 'PREZKOUSENI' END;
