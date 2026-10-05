-- 001 data: kategorie, typy a letadla podle zadání uživatele (5. 10. 2026).

INSERT INTO lkkl.lov_kategorie (nazev) VALUES
    ('Kluzák'),
    ('Motorový kluzák'),
    ('Letoun'),
    ('Ultralehký letoun');

INSERT INTO lkkl.lov_typ (nazev, kategorie_id)
SELECT v.typ, k.id
FROM (VALUES
    ('L 13',            'Kluzák'),
    ('L 13 Vivat',      'Motorový kluzák'),
    ('VSO 10',          'Kluzák'),
    ('Z 126',           'Letoun'),
    ('ASW 20',          'Kluzák'),
    ('ASW 15',          'Kluzák'),
    ('Cessna F 172',    'Letoun'),
    ('AirLony Skylane', 'Ultralehký letoun'),
    ('Z 526',           'Letoun')
) AS v(typ, kategorie)
JOIN lkkl.lov_kategorie k ON k.nazev = v.kategorie;

INSERT INTO lkkl.letadlo (rejstrik, typ_id, soukrome)
SELECT v.rejstrik, t.id, v.soukrome
FROM (VALUES
    ('OK-3819',    'L 13',            false),
    ('OK-2817',    'L 13',            false),
    ('OK-2728',    'L 13',            false),
    ('OK-7114',    'L 13 Vivat',      false),
    ('OK-5626',    'VSO 10',          false),
    ('OK-6512',    'VSO 10',          false),
    ('OK-MFV',     'Z 126',           false),
    ('OK-6722',    'ASW 20',          false),
    ('OK-8656',    'ASW 15',          false),
    ('OK-CWF',     'Cessna F 172',    false),
    ('OK-0914',    'ASW 15',          false),
    ('OK-CUO 78',  'AirLony Skylane', false),
    ('OK-CRA',     'Z 526',           true)
) AS v(rejstrik, typ, soukrome)
JOIN lkkl.lov_typ t ON t.nazev = v.typ;
