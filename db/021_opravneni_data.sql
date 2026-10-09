-- 021 data: druhy oprávnění instruktorů a examinátorů, kategorie letadel, pro které se smí
-- vydat, a role v letu, ke kterým opravňují (docs/navrh-opravneni.md). Vlekař a role v letu
-- jsou ve struktuře (021, 024); kategorie vlekaře zde pro novou databázi (server: 024). Kdo má jaké oprávnění a pro které kategorie,
-- zadává správce v aplikaci (Osoby → detail → Oprávnění; kontrola: v_osoba_opravneni).
-- Na serveru provedeno 7. 10. 2026 a převedeno skriptem 024; pro novou databázi (po všech
-- skriptech struktury): psql -1 -f db/021_opravneni_data.sql

INSERT INTO lkkl.lov_opravneni (kod, nazev, poradi) VALUES
    ('FI_S',           'FI(S) – instruktor kluzáků',               10),
    ('FE_S',           'FE(S) – examinátor kluzáků',               20),
    ('FI_A',           'FI(A) – instruktor letounů',               30),
    ('CRI_A',          'CRI(A) – instruktor třídní kvalifikace',   40),
    ('FE_A',           'FE(A) – examinátor letounů',               50),
    ('CRE_A',          'CRE(A) – examinátor třídní kvalifikace',   55),
    ('INSTRUKTOR_ULL', 'Instruktor ULL',                           60),
    ('INSPEKTOR_ULL',  'Inspektor provozu ULL',                    70);

-- Kategorie: kluzákoví instruktoři a examinátoři na kluzácích a TMG, letounoví na letounech
-- a TMG, ULL na ultralehkých. Kategorie, která v databázi není, se přeskočí.
INSERT INTO lkkl.lov_opravneni_kategorie (opravneni_id, kategorie_id)
SELECT o.id, k.id
FROM (VALUES
    ('FI_S', 'KLUZAK'), ('FI_S', 'TMG'),
    ('FE_S', 'KLUZAK'), ('FE_S', 'TMG'),
    ('FI_A', 'LETOUN'), ('FI_A', 'TMG'),
    ('CRI_A', 'LETOUN'), ('CRI_A', 'TMG'),
    ('FE_A', 'LETOUN'), ('FE_A', 'TMG'),
    ('CRE_A', 'LETOUN'), ('CRE_A', 'TMG'),
    ('INSTRUKTOR_ULL', 'UL'),
    ('INSPEKTOR_ULL', 'UL'),
    ('VLEKAR', 'LETOUN'), ('VLEKAR', 'UL')
) AS v(opravneni, kategorie)
JOIN lkkl.lov_opravneni o ON o.kod = v.opravneni
JOIN lkkl.lov_kategorie k ON k.kod = v.kategorie
ON CONFLICT DO NOTHING;

-- Role: instruktoři vedou výcvik a dozorují sóla (docs/podklady/prezkouseni.md). Kdo smí
-- přezkoušet, určuje typ přezkoušení (041_prezkouseni_data.sql), ne role.
INSERT INTO lkkl.lov_opravneni_role (opravneni_id, role_id)
SELECT o.id, r.id
FROM (VALUES
    ('FI_S', 'INSTRUKTOR'), ('FI_S', 'DOZOR'),
    ('FI_A', 'INSTRUKTOR'), ('FI_A', 'DOZOR'),
    ('CRI_A', 'INSTRUKTOR'), ('CRI_A', 'DOZOR'),
    ('INSTRUKTOR_ULL', 'INSTRUKTOR'), ('INSTRUKTOR_ULL', 'DOZOR')
) AS v(opravneni, role)
JOIN lkkl.lov_opravneni o ON o.kod = v.opravneni
JOIN lkkl.lov_role r      ON r.kod = v.role;
