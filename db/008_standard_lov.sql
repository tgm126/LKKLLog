-- 008: jednotný standard číselníků (lov_*) a číselníky pro lety.
--
-- Standard číselníku:
--   id     – primární klíč; vazby mezi tabulkami jsou VŽDY přes id
--   kod    – jedinečný, jen pro program (nikde se nezobrazuje); doména lkkl.kod
--   nazev  – text pro zobrazení; jde měnit a nemusí být jedinečný; doména lkkl.nazev
--   poradi – pořadí v nabídkách; doména lkkl.poradi
--   platny – přepínač „používat“; neplatná položka se nenabízí, stará data na ni dál odkazují.
--            Použitou položku nepustí smazat cizí klíč; nepoužitou (překlep) smazat jde.
-- Pravidla jednotlivých sloupců jsou v doménách – definovaná jednou pro všechny číselníky.

CREATE DOMAIN lkkl.kod AS text CHECK (VALUE ~ '^[A-Z0-9_]+$');
COMMENT ON DOMAIN lkkl.kod IS 'Interní kód položky číselníku pro program: velká písmena, číslice, podtržítko.';

CREATE DOMAIN lkkl.nazev AS text CHECK (btrim(VALUE) <> '');
COMMENT ON DOMAIN lkkl.nazev IS 'Text pro zobrazení v aplikaci; nesmí být prázdný.';

CREATE DOMAIN lkkl.poradi AS smallint DEFAULT 100 CHECK (VALUE >= 0);
COMMENT ON DOMAIN lkkl.poradi IS 'Pořadí v nabídkách (menší = výš).';

CREATE DOMAIN lkkl.platny AS boolean DEFAULT true;
COMMENT ON DOMAIN lkkl.platny IS 'Položka se používá (nabízí). Neplatná se nenabízí, ale nemaže.';

-- Pohled závisí na sloupcích, které se mění – po změnách se založí znovu.
DROP VIEW lkkl.v_letadlo;

-- --- lov_kategorie ---------------------------------------------------------------------------
ALTER TABLE lkkl.lov_kategorie
    DROP CONSTRAINT lov_kategorie_nazev_key,
    DROP CONSTRAINT lov_kategorie_nazev_check,
    ALTER COLUMN nazev TYPE lkkl.nazev,
    ADD COLUMN kod lkkl.kod,
    ADD COLUMN poradi lkkl.poradi NOT NULL,
    ADD COLUMN platny lkkl.platny NOT NULL;

UPDATE lkkl.lov_kategorie k SET kod = v.kod, poradi = v.poradi
FROM (VALUES ('Kluzák', 'KLUZAK', 10), ('Motorový kluzák', 'TMG', 20),
             ('Letoun', 'LETOUN', 30), ('Ultralehký letoun', 'UL', 40)) AS v(nazev, kod, poradi)
WHERE k.nazev = v.nazev;
UPDATE lkkl.lov_kategorie SET kod = 'KATEGORIE_' || id WHERE kod IS NULL;  -- přejmenované ručně

ALTER TABLE lkkl.lov_kategorie ALTER COLUMN kod SET NOT NULL, ADD UNIQUE (kod);

-- --- lov_typ ---------------------------------------------------------------------------------
ALTER TABLE lkkl.lov_typ
    DROP CONSTRAINT lov_typ_nazev_key,
    DROP CONSTRAINT lov_typ_nazev_check,
    ALTER COLUMN nazev TYPE lkkl.nazev,
    ADD COLUMN kod lkkl.kod,
    ADD COLUMN poradi lkkl.poradi NOT NULL,
    ADD COLUMN platny lkkl.platny NOT NULL;

UPDATE lkkl.lov_typ t SET kod = v.kod
FROM (VALUES ('L 13', 'L13'), ('L 13 Vivat', 'L13_VIVAT'), ('VSO 10', 'VSO10'),
             ('Z 126', 'Z126'), ('Z 526', 'Z526'), ('ASW 15', 'ASW15'), ('ASW 20', 'ASW20'),
             ('Cessna F 172', 'C172'), ('AirLony Skylane', 'SKYLANE')) AS v(nazev, kod)
WHERE t.nazev = v.nazev;
UPDATE lkkl.lov_typ SET kod = 'TYP_' || id WHERE kod IS NULL;

ALTER TABLE lkkl.lov_typ ALTER COLUMN kod SET NOT NULL, ADD UNIQUE (kod);

-- --- lov_letiste: kódem je přímo ICAO (sloupec icao se přejmenuje, aby údaj nebyl dvakrát) ----
ALTER TABLE lkkl.lov_letiste RENAME COLUMN icao TO kod;
ALTER TABLE lkkl.lov_letiste RENAME CONSTRAINT lov_letiste_icao_key TO lov_letiste_kod_key;
ALTER TABLE lkkl.lov_letiste RENAME CONSTRAINT lov_letiste_icao_check TO lov_letiste_kod_icao;
ALTER TABLE lkkl.lov_letiste
    DROP CONSTRAINT lov_letiste_nazev_key,
    DROP CONSTRAINT lov_letiste_nazev_check,
    ALTER COLUMN nazev TYPE lkkl.nazev,
    ALTER COLUMN kod TYPE lkkl.kod,
    ALTER COLUMN kod SET NOT NULL,
    ADD COLUMN poradi lkkl.poradi NOT NULL,
    ADD COLUMN platny lkkl.platny NOT NULL;
COMMENT ON COLUMN lkkl.lov_letiste.kod IS 'Kód ICAO (4 velká písmena) – zároveň kód číselníku.';

-- --- číselníky pro lety ----------------------------------------------------------------------
-- Hodnoty s kódem patří do struktury (ne do dat): program podle kódu uplatňuje pravidla.
-- Názvy a pořadí jde měnit.

CREATE TABLE lkkl.lov_ucel (
    id     bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    kod    lkkl.kod    NOT NULL UNIQUE,
    nazev  lkkl.nazev  NOT NULL,
    poradi lkkl.poradi NOT NULL,
    platny lkkl.platny NOT NULL
);
COMMENT ON TABLE lkkl.lov_ucel IS 'Účel letu. Vlek není účel – odvodí se z vazby kluzák–vlečná.';
INSERT INTO lkkl.lov_ucel (kod, nazev, poradi) VALUES
    ('NORMALNI', 'Normální', 10),
    ('VYCVIK', 'Výcvik', 20),
    ('VYCVIK_SOLO', 'Výcvik sólo', 30),
    ('PREZKOUSENI', 'Přezkoušení', 40);

CREATE TABLE lkkl.lov_zpusob_vzletu (
    id     bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    kod    lkkl.kod    NOT NULL UNIQUE,
    nazev  lkkl.nazev  NOT NULL,
    poradi lkkl.poradi NOT NULL,
    platny lkkl.platny NOT NULL
);
COMMENT ON TABLE lkkl.lov_zpusob_vzletu IS 'Způsob vzletu.';
INSERT INTO lkkl.lov_zpusob_vzletu (kod, nazev, poradi) VALUES
    ('VLASTNI', 'Vlastní (motorem)', 10),
    ('NAVIJAK', 'Naviják', 20),
    ('VLEK', 'Aerovlek', 30);

CREATE TABLE lkkl.lov_funkce (
    id         bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    kod        lkkl.kod    NOT NULL UNIQUE,
    nazev      lkkl.nazev  NOT NULL,
    poradi     lkkl.poradi NOT NULL,
    platny     lkkl.platny NOT NULL,
    na_palube  boolean     NOT NULL DEFAULT true
);
COMMENT ON TABLE lkkl.lov_funkce IS 'Funkce osoby jmenovitě uvedené u letu; ostatní lidé na palubě jsou jen v POB.';
COMMENT ON COLUMN lkkl.lov_funkce.na_palube IS 'Osoba je v letadle (počítá se do POB). Dozor je na zemi.';
INSERT INTO lkkl.lov_funkce (kod, nazev, poradi, na_palube) VALUES
    ('PIC', 'PIC', 10, true),
    ('ZAK', 'Žák', 20, true),
    ('PREZKOUSENY', 'Přezkoušený', 30, true),
    ('DOZOR', 'Dozor (na zemi)', 40, false);

CREATE TABLE lkkl.lov_duvod_zruseni (
    id     bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    kod    lkkl.kod    NOT NULL UNIQUE,
    nazev  lkkl.nazev  NOT NULL,
    poradi lkkl.poradi NOT NULL,
    platny lkkl.platny NOT NULL
);
COMMENT ON TABLE lkkl.lov_duvod_zruseni IS 'Důvod zrušení letu (let se nemaže).';
INSERT INTO lkkl.lov_duvod_zruseni (kod, nazev, poradi) VALUES
    ('TECHNICKA_ZAVADA', 'Technická závada', 10),
    ('POCASI', 'Počasí', 20),
    ('OMYL', 'Založeno omylem', 30),
    ('PRERUSENY_VZLET', 'Přerušený vzlet', 40),
    ('JINE', 'Jiné', 50);

-- --- pohled na letadla (beze změny obsahu) ---------------------------------------------------
CREATE VIEW lkkl.v_letadlo AS
SELECT l.id,
       l.rejstrik,
       t.nazev AS typ,
       k.nazev AS kategorie,
       l.soukrome,
       t.pocet_mist,
       l.max_doba_min,
       l.vlecne
FROM lkkl.letadlo l
JOIN lkkl.lov_typ t       ON t.id = l.typ_id
JOIN lkkl.lov_kategorie k ON k.id = t.kategorie_id;
COMMENT ON VIEW lkkl.v_letadlo IS 'Letadla s názvem typu, kategorií a počtem míst (z typu).';
