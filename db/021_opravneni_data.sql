-- 021 data: druhy oprávnění instruktorů a examinátorů, kategorie letadel, pro které platí,
-- a role v letu, ke kterým opravňují (docs/podklady/instruktori-a-examinatori.md).
-- Vlekař je ve struktuře (021_opravneni.sql, role z 022). Kdo má jaké oprávnění, zadává
-- správce do lkkl.lov_osoba_opravneni (kontrola: v_osoba_opravneni).
-- Na serveru provedeno 7. 10. 2026 (role tam vznikly převodem v 022); pro novou databázi:
-- psql -1 -f db/021_opravneni_data.sql

INSERT INTO lkkl.lov_opravneni (kod, nazev, poradi, omezene) VALUES
    ('FI_S',           'FI(S) – instruktor kluzáků',               10, false),
    ('FI_S_OMEZENY',   'FI(S) omezený – pod dohledem',             15, true),
    ('FE_S',           'FE(S) – examinátor kluzáků',               20, false),
    ('FI_A',           'FI(A) – instruktor letounů',               30, false),
    ('FI_A_OMEZENY',   'FI(A) omezený – pod dohledem',             35, true),
    ('CRI_A',          'CRI(A) – instruktor třídní kvalifikace',   40, false),
    ('FE_A',           'FE(A) – examinátor letounů',               50, false),
    ('CRE_A',          'CRE(A) – examinátor třídní kvalifikace',   55, false),
    ('INSTRUKTOR_ULL', 'Instruktor ULL',                           60, false),
    ('INSPEKTOR_ULL',  'Inspektor provozu ULL',                    70, false);

-- Kategorie: kluzákoví instruktoři a examinátoři na kluzácích a TMG, letounoví na letounech
-- a TMG, ULL na ultralehkých. Kategorie, která v databázi není, se přeskočí.
INSERT INTO lkkl.lov_opravneni_kategorie (opravneni_id, kategorie_id)
SELECT o.id, k.id
FROM (VALUES
    ('FI_S', 'KLUZAK'), ('FI_S', 'TMG'),
    ('FI_S_OMEZENY', 'KLUZAK'), ('FI_S_OMEZENY', 'TMG'),
    ('FE_S', 'KLUZAK'), ('FE_S', 'TMG'),
    ('FI_A', 'LETOUN'), ('FI_A', 'TMG'),
    ('FI_A_OMEZENY', 'LETOUN'), ('FI_A_OMEZENY', 'TMG'),
    ('CRI_A', 'LETOUN'), ('CRI_A', 'TMG'),
    ('FE_A', 'LETOUN'), ('FE_A', 'TMG'),
    ('CRE_A', 'LETOUN'), ('CRE_A', 'TMG'),
    ('INSTRUKTOR_ULL', 'UL'),
    ('INSPEKTOR_ULL', 'UL')
) AS v(opravneni, kategorie)
JOIN lkkl.lov_opravneni o ON o.kod = v.opravneni
JOIN lkkl.lov_kategorie k ON k.kod = v.kategorie;

-- Role (testovací naplnění, správce upraví): instruktoři i examinátoři výcvik · PIC,
-- sólo · dozor a přezkoušení · PIC.
INSERT INTO lkkl.lov_opravneni_role (opravneni_id, ucel_id, funkce_id)
SELECT o.id, u.id, f.id
FROM lkkl.lov_opravneni o
CROSS JOIN (VALUES ('VYCVIK', 'PIC'), ('VYCVIK_SOLO', 'DOZOR'), ('PREZKOUSENI', 'PIC')) AS r(ucel, funkce)
JOIN lkkl.lov_ucel u   ON u.kod = r.ucel
JOIN lkkl.lov_funkce f ON f.kod = r.funkce
WHERE o.kod <> 'VLEKAR';
