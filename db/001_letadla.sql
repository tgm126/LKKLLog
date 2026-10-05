-- 001: kategorie a typy letadel (číselníky), letadla.
-- Kategorii určuje typ (L 13 je vždy kluzák), proto ji letadlo nemá – ukazuje ji pohled.

CREATE SCHEMA lkkl;

CREATE TABLE lkkl.lov_kategorie (
    id    bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nazev text NOT NULL UNIQUE CHECK (btrim(nazev) <> '')
);
COMMENT ON TABLE lkkl.lov_kategorie IS 'Kategorie letadel (kluzák, motorový kluzák, letoun, ultralehký letoun).';

CREATE TABLE lkkl.lov_typ (
    id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nazev        text   NOT NULL UNIQUE CHECK (btrim(nazev) <> ''),
    kategorie_id bigint NOT NULL REFERENCES lkkl.lov_kategorie
);
COMMENT ON TABLE lkkl.lov_typ IS 'Typy letadel; typ určuje kategorii.';

CREATE TABLE lkkl.letadlo (
    id           bigint   GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    rejstrik     text     NOT NULL UNIQUE
                          CHECK (rejstrik <> '' AND rejstrik = upper(btrim(rejstrik))),
    typ_id       bigint   NOT NULL REFERENCES lkkl.lov_typ,
    soukrome     boolean  NOT NULL DEFAULT false,
    pocet_mist   smallint CHECK (pocet_mist > 0),
    max_doba_min integer  CHECK (max_doba_min > 0),
    vlecne       boolean  NOT NULL DEFAULT false
);
COMMENT ON TABLE lkkl.letadlo IS 'Letadla klubu i soukromá.';
COMMENT ON COLUMN lkkl.letadlo.rejstrik IS 'Rejstříková značka, např. OK-3819; ultralehká s mezerou (OK-CUO 78).';
COMMENT ON COLUMN lkkl.letadlo.soukrome IS 'Soukromé letadlo (vlastník není klub).';
COMMENT ON COLUMN lkkl.letadlo.pocet_mist IS 'Počet míst včetně pilota; prázdné = nezadáno.';
COMMENT ON COLUMN lkkl.letadlo.max_doba_min IS 'Maximální doba letu v minutách; prázdné = nezadáno.';
COMMENT ON COLUMN lkkl.letadlo.vlecne IS 'Letadlo může vlekat kluzáky.';

CREATE VIEW lkkl.v_letadlo AS
SELECT l.id,
       l.rejstrik,
       t.nazev AS typ,
       k.nazev AS kategorie,
       l.soukrome,
       l.pocet_mist,
       l.max_doba_min,
       l.vlecne
FROM lkkl.letadlo l
JOIN lkkl.lov_typ t       ON t.id = l.typ_id
JOIN lkkl.lov_kategorie k ON k.id = t.kategorie_id;
COMMENT ON VIEW lkkl.v_letadlo IS 'Letadla s názvem typu a kategorií.';
