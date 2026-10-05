-- 003: letiště (číselník). Přistání do terénu sem nepatří – řeší se u letu.

CREATE TABLE lkkl.lov_letiste (
    id            bigint       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    icao          text         UNIQUE CHECK (icao ~ '^[A-Z]{4}$'),
    nazev         text         NOT NULL UNIQUE CHECK (btrim(nazev) <> ''),
    domovske      boolean      NOT NULL DEFAULT false,
    zem_sirka     numeric(8,5) CHECK (zem_sirka BETWEEN -90 AND 90),
    zem_delka     numeric(8,5) CHECK (zem_delka BETWEEN -180 AND 180),
    nadm_vyska_ft integer
);
COMMENT ON TABLE lkkl.lov_letiste IS 'Letiště a plochy (i bez kódu ICAO).';
COMMENT ON COLUMN lkkl.lov_letiste.icao IS 'Kód ICAO (4 velká písmena); plochy bez kódu prázdné.';
COMMENT ON COLUMN lkkl.lov_letiste.domovske IS 'Domovské letiště klubu (nejvýš jedno).';
COMMENT ON COLUMN lkkl.lov_letiste.zem_sirka IS 'Zeměpisná šířka ve stupních (WGS 84), sever kladně.';
COMMENT ON COLUMN lkkl.lov_letiste.zem_delka IS 'Zeměpisná délka ve stupních (WGS 84), východ kladně.';
COMMENT ON COLUMN lkkl.lov_letiste.nadm_vyska_ft IS 'Nadmořská výška ve stopách (jako v AIP).';

CREATE UNIQUE INDEX lov_letiste_jedno_domovske ON lkkl.lov_letiste (domovske) WHERE domovske;
