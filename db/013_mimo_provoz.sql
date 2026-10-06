-- 013: letadlo mimo provoz (prodané, dlouhodobá oprava, porucha) a nabídka letadel pro průvodce.
-- Letadlo mimo provoz se v nabídce neobjeví, jeho lety zůstávají.

ALTER TABLE lkkl.letadlo ADD COLUMN mimo_provoz boolean NOT NULL DEFAULT false;
COMMENT ON COLUMN lkkl.letadlo.mimo_provoz IS 'Letadlo se nenabízí pro nové lety (prodané, oprava, porucha); stará data zůstávají.';

INSERT INTO lkkl.audit_popisek (tabulka, sloupec, popisek, poradi) VALUES
    ('letadlo', 'mimo_provoz', 'mimo provoz', 60);

CREATE OR REPLACE VIEW lkkl.v_letadlo AS
SELECT l.id,
       l.rejstrik,
       t.nazev AS typ,
       k.nazev AS kategorie,
       l.soukrome,
       t.pocet_mist,
       l.max_doba_min,
       l.vlecne,
       l.mimo_provoz
FROM lkkl.letadlo l
JOIN lkkl.lov_typ t       ON t.id = l.typ_id
JOIN lkkl.lov_kategorie k ON k.id = t.kategorie_id;

-- Nabídka pro průvodce novým letem: jen letadla v provozu, stálé pořadí
-- (kategorie, typ, rejstřík – podle pořadí v číselnících).
CREATE VIEW lkkl.v_letadlo_nabidka AS
SELECT l.id,
       l.rejstrik,
       t.nazev AS typ,
       k.nazev AS kategorie,
       k.kod   AS kategorie_kod,
       l.vlecne,
       l.soukrome
FROM lkkl.letadlo l
JOIN lkkl.lov_typ t       ON t.id = l.typ_id
JOIN lkkl.lov_kategorie k ON k.id = t.kategorie_id
WHERE NOT l.mimo_provoz
ORDER BY k.poradi, t.poradi, t.nazev, l.rejstrik;
COMMENT ON VIEW lkkl.v_letadlo_nabidka IS 'Nabídka letadel pro nový let: jen v provozu, ve stálém pořadí.';
